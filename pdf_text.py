import csv
import json
import os
import re

import fitz  # PyMuPDF
import pdfplumber
import pdftotext
import pytesseract
from flask import Flask, jsonify, request
from PIL import Image

app = Flask(__name__)

def clean_cell(cell, characters_to_remove):
        if cell is not None:
            return cell.replace(characters_to_remove, "")
        return cell

def extract_images_from_pdf(pdf_file_path, page_num, output_folder):
    # Open the PDF file
    pdf_document = fitz.open(pdf_file_path)

    try:
        # Get the specified page
        page = pdf_document[page_num]

        # Get all the images on the page
        image_list = page.get_images(full=True)

        for i, img in enumerate(image_list):
            xref = img[0]
            base_image = pdf_document.extract_image(xref)
            image_bytes = base_image["image"]

            # Determine the image format (extension)
            image_format = base_image["ext"]

            output_image_path = f"{output_folder}/image_{i}.{image_format}"

            with open(output_image_path, "wb") as image_file:
                image_file.write(image_bytes)

            # print(f"Image {i} extracted and saved to {output_image_path}")
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        # Close the PDF document
        pdf_document.close()

def keyword_in_image(image_path, keyword):
    for file in os.listdir(image_path): 
        file_created=False
        # Check whether file is in text format or not 
        if file.endswith(".png"): 
            file_path = f"{image_path}{file}"
            # Open the image using PIL (Pillow)
            image = Image.open(file_path)
            
            # Perform OCR on the image to extract text
            extracted_text = pytesseract.image_to_string(image)
            for key in keyword:
                if key in str(extracted_text):
                    with open("data.txt", "w") as outfile:
                        outfile.write(extracted_text)
                        file_created = True
        if file_created:
            # Read the data from "data.txt"
            with open("data.txt", "r") as infile:
                data = infile.readlines()

            # Create a list to store the extracted data as dictionaries
            property_list = []

            # Iterate through each line of the data
            for line in data:
                # Split the line based on spaces and remove empty elements
                elements = line.strip().split()
                for ele in elements:
                    if ele == '_' or ele == '__':
                        elements.remove(ele)
                    if ele == 'tof':
                        elements.remove(ele)

                # Check if there are at least 5 elements in the line (Property, Unit#, Rooms, Vacant/Occupied, Current)
                if len(elements) >= 5:
                    
                    if len(elements) == 5:
                        # If the length is 5, set the "Property" field to an empty string
                        property_info = {
                            "Property": "",
                            "Unit#": elements[0],
                            "Rooms": elements[1],
                            "Vacant/Occupied": elements[2],
                            "Current": elements[3],
                            "Immediate Potential": elements[4]
                        }
                    else:
                        # If the length is 6, use all values
                        try:
                            property_info = {
                                "Property": f'{elements[0]} {elements[1]}',
                                "Unit#": elements[2],
                                "Rooms": elements[3],
                                "Vacant/Occupied": elements[4],
                                "Current": elements[5],
                                "Immediate Potential": elements[6]
                            }
                        except:
                            print(len(elements), elements)
                    property_list.append(property_info)
            
            # Convert the list of dictionaries to JSON
            json_data = json.dumps(property_list, indent=2)

            with open("final.json", "w") as json_file:
                json_file.write(json_data)

# path = '/home/sidhi/pdf_dir/'
# os.chdir(path)
@app.route('/process_pdf', methods=['POST'])
def process_pdf():
    pdf_file = request.files['pdf_file']
    os.makedirs("uploaded_files", exist_ok=True)
    pdf_filename = pdf_file.filename
    pdf_path = f"uploaded_files/{pdf_filename}"
    pdf_file.save(pdf_path)
    # iterate through all file 
    search_keywords = ['FINANCIAL ANALYSIS','Financial Analysis', 'RENT ROLL', 'Rent Roll']  # Add your desired keywords here
    with open(pdf_path, "rb") as f:
        pdf = pdftotext.PDF(f)

    # Define the keywords you want to search for
    
    page_nos = []
    found_key = ''
    spotted = False
    # Iterate through the pages and search for keywords
    for page_number, page_text in enumerate(pdf):
        for keyword in search_keywords:
            if 'Casa' in page_text:
                spotted = True
            if keyword in page_text:
                found_key = keyword
                page_nos.append(page_number)
    if found_key == 'RENT ROLL' or found_key == 'Rent Roll':
        # print(found_key)
        if len(page_nos) > 0:
            page_texts = []
            for page in page_nos:
                page_texts.append(pdf[page])
            
            # Concatenate the page texts into a single string
            all_page_text = '\n'.join(page_texts)
            # print(all_page_text)
        else:
            print("No pages containing the keywords were found.")

        with open("sample1.txt", "w") as outfile:
            outfile.write(all_page_text)

        lines = str(all_page_text).strip().split('\n')

        if spotted:
            index = [6]
        else:
            index = [1, 2, 3, 4]
        
        skip_rows = 1
        # Extract keys from the header
        for ind in index:
            split_string = lines[ind].split("  ")
            testing_string = []
            for string in split_string:
                if string != '':
                    if string[0] == ' ':
                        string = string[1:]
                    fr = string.split(' ')
                    if len(fr)==4:
                        testing_string.append(f'{fr[0]} {fr[1]}')
                        testing_string.append(f'{fr[2]} {fr[3]}')
                    elif len(fr) == 3:
                        testing_string.append(f'{fr[0]} {fr[1]}')
                        testing_string.append(f'{fr[2]}')
                    else:
                        testing_string.append(string)
            if len(testing_string)>=4:
                skip_rows=ind
                break
        a = []
        keys = []

        try:
            for data in split_string:
                if data == split_string[0] and data[0] != ' ':
                    h = data.split(' ')
                    for o in h:
                        a.append(o)
                elif ':' in data:
                    split_text = data.split(':')
                    for j in range(len(split_text)):
                        a.append(split_text[j])
                else:
                    a.append(data)
            for elem in a:
                if elem != '':
                    if elem == 'Expiration':
                        elem = f'Lease {elem}'
                    keys.append(elem)
        except:
            keys = testing_string

        for kh in range(len(keys)):
            if keys[kh] == 'RATE':
                new = f'{keys[kh-1]} {keys[kh]}'
                keys.pop(kh)
                keys.pop(kh-1)
                keys.insert(kh-1, new)
                break
            elif 'SQ' in keys[kh]:
                ds = keys[kh].split(' ')
                if len(ds)>1:
                    keys.pop(kh)
                    keys.insert(kh,ds[0])
                    keys.insert(kh+1,'SQFT')
            elif 'FT' in keys[kh]:
                ds = keys[kh].split(' ')
                if len(ds)>1:
                    keys.pop(kh)
                    keys.insert(kh,ds[1])

        list1 = []

        with open('sample1.txt') as csvfile:
            filereader = csv.reader(csvfile, delimiter="\t")
            for row in filereader:
                
                row = str(row).replace(",", ".")
                b = str(row).replace("    ",",")
                b = str(b).replace("   ",",")
                test_string_parts = b.split(',')
                null_count = 0
                value_list = []
                for i in test_string_parts:
                    if i != '':
                        null_count=0
                        value_list.append(i)
                    else:
                        null_count+=1
                        if null_count==4:
                            value_list.append('')
                            null_count=0

                # Iterate over the data and create dictionaries
                for rows in value_list:
                    # Check if we need to skip this row (header rows)
                    if skip_rows > 0:
                        skip_rows -= 1
                        continue
                val = [str(elem).replace("['", '').replace("']",'') for elem in value_list]
                if str(val[-1]).isnumeric():
                    val.append('')
                
                val1=[]
                store = ''
                for d in range(len(val)):
                    
                    if val[d] != '' and val[d] == val[0] and val[d][0] != ' ':
                        if '  ' in val[d]:
                            split_text = str(val[d]).split('  ')
                        else:
                            split_text = str(val[d]).split(' ')
                        for l in split_text:
                            if l != '':
                                val1.append(l)
                    elif '  ' in val[d]:
                        
                        if '  $' in val[d]:
                            if val[d] == '  $':
                                store = '$'
                                val1.append('$')
                            else:
                                val1.append(val[d])
                        else:
                            split_text = str(val[d]).split('  ')
                            for l in split_text:
                                if l != '':
                                    if '/' in l and '.' in l:
                                        txt = str(l).split(' ')
                                        if len(txt)>1:
                                            a = str(txt[1]).replace('/', '-')
                                            b = str(a).split('-')
                                            c = ''
                                            for k in range(len(b)):
                                                if len(b[k])<2:
                                                    c = c + f'0{b[k]}-'
                                                else:
                                                    c = c+f'{b[k]}-'
                                            if c[-1] == '-':
                                                c = c[:-1]
                                            pattern_str = r'^\d{2}-\d{2}-\d{4}$'
                                            if re.match(pattern_str, c):
                                                val1.append(f'{store} {txt[0]}')
                                                val1.append(txt[1])
                                            else:
                                                val1.append(l)
                                        else:
                                            val1.append(l)
                                    else:
                                        val1.append(l)
                    elif '/' in val[d] and '.' in val[d]:
                        split_text = str(val[d]).split(' ')
                        a = str(split_text[1]).replace('/', '-')
                        b = str(a).split('-')
                        c = ''
                        for k in range(len(b)):
                            if len(b[k])<2:
                                c = c + f'0{b[k]}-'
                            else:
                                c = c+f'{b[k]}-'
                        if c[-1] == '-':
                            c = c[:-1]
                        pattern_str = r'^\d{2}-\d{2}-\d{4}$'
                        if re.match(pattern_str, c):
                            val1.append(f'{store} {split_text[0]}')
                            val1.append(split_text[1])
                        else:
                            val1.append(val[d])
                    elif '- $' in val[d]:
                        s = str(val[d]).split(' ')
                        new = f'{store} {s[0]}'
                        if val1[d-1] == '':
                            val1.pop(d-2)
                            val1.insert(d-2, new)
                            val1.pop(d-1)
                            val1.append(s[1])
                            store = s[1]
                        elif val1[d-1] == '$':
                            new = f'{store} {s[0]}'
                            val1.pop(d-1)
                            val1.insert(d-1, new)
                            val1.append(s[1])
                            store = s[1]
                        else:
                            if store == '$':
                                val1.append(s[0])
                                store = s[1] 
                    elif '.' in val[d] and '$' in val[d]:
                        if '  ' in val[d]:
                            val[d] = val[d].replace('  ', '')
                        if val[d][0] == ' ':
                            val[d] = val[d][1:-1]
                        t = str(val[d]).split(' ')
                        new = f'{store} {t[0]}'
                        if len(t) == 2:
                            store = t[1]
                        val1.append(new)
                    elif '-' in val[d]:
                        split_text = str(val[d]).split(' ')
                        if split_text[0] == '-':
                            val1.append(f'{store} {split_text[0]}')
                            if len(split_text)>1:
                                val1.append(split_text[1])
                            else:
                                val1.append("")
                        else:
                            val1.append(val[d])
                    else:
                        if ' ' in val[d]:
                            split_text = str(val[d]).split(' ')
                            if split_text[1].isnumeric():
                                for l in split_text:
                                    if l != '':
                                        val1.append(l)
                            else:
                                val1.append(val[d])
                        else:
                            val1.append(val[d])
                for item in val1:
                    if item == "$":
                        val1.remove(item)
                if val1[0] == '':
                    val1.remove(val1[0])
                
                if len(val1)>len(keys):
                    val2 = []
                    length_diff = len(val1)-len(keys)
                    loop_count = 0
                    for it in val1:
                        if it== '':
                            val1.remove(it)
                            loop_count += 1
                        if loop_count == length_diff:
                            break

                if ' VAC' in val1 and len(val1)<len(keys):
                    length_diff = len(keys)-len(val1)
                    for i in range(length_diff+1):
                        val1.append('')
                if len(val1)<len(keys):
                    pass
                else:
                    data_dict = dict(zip(keys, val1))

                    list1.append(data_dict)

        json_response = json.dumps(list1, indent=4)
        
        with open("final.json", "w") as json_file:
            json_file.write(json_response)

    if found_key == 'Financial Analysis' or found_key == 'FINANCIAL ANALYSIS':
        pdf = pdfplumber.open(pdf_path)
        heading_pattern = r"Financial\s+Analysis" 
        
        pages_with_heading = []

        spotted_key = ''
        for page_number, page in enumerate(pdf.pages, start=1):
            text = page.extract_text()
            if re.search(heading_pattern, text, re.IGNORECASE): 
                pages_with_heading.append(page_number)
            if 'Westwood' in text:
                spotted_key = 'Westwood'
            if 'Jackson' in text:
                spotted_key = 'Jackson'
            if 'TRAVIS' in text:
                spotted_key = 'TRAVIS'
            if 'Independence Meadows' in text:
                spotted_key = 'Independence Meadows'
        
        if spotted_key == 'Westwood':
            all_tables = []

            characters_to_remove = '\n'  

            for page_number in pages_with_heading:
            
                page = pdf.pages[page_number - 1]  
                tables = page.extract_tables()

                if len(tables) > 0:
                
                    header_row_1 = tables[0][0]

                    if header_row_1 is not None:
                    
                        data = []
                        for row in tables[0]:
                            cleaned_row = [clean_cell(cell, characters_to_remove) for cell in row]
                            row_data = {header_row_1[i]: cleaned_row[i] for i in range(len(header_row_1))}
                            data.append(row_data)

                        all_tables.append(data)

            combined_data = [row for table_data in all_tables for row in table_data]

            json_data = json.dumps(combined_data, indent=4)
            with open("final.json", "w") as json_file:
                json_file.write(json_data)

        elif spotted_key == 'Jackson':
            page_number_to_extract = pages_with_heading[1]


            page = pdf.pages[page_number_to_extract ]  
            tables = page.extract_tables()

            if len(tables) >= 2:

                table_2 = tables[1]

                header_row = table_2[0]


                data = []

                for row in table_2[1:]:
                    row_data = {header_row[i].replace('\n', ' '): cell.replace('\n', ' ') for i, cell in enumerate(row)}
                    data.append(row_data)


                json_data = json.dumps(data, indent=4)

                with open(f"final.json", "w") as json_file:
                    json_file.write(json_data)

                table_3 = tables[2]
                

                header_row = table_3[0]

                data = []


                for row in table_3[1:]:
                    row_data = {header_row[i].replace('\n', ' '): cell.replace('\n', ' ') for i, cell in enumerate(row)}
                    data.append(row_data)


                json_data = json.dumps(data, indent=4)

                # Save the JSON data to a file
                with open(f"final.json", "a") as json_file:
                    json_file.write(json_data)

        elif spotted_key == 'Independence Meadows':
            with open(pdf_path, "rb") as f:
                pdf = pdftotext.PDF(f)

            all_data = []

            page_texts = pdf[28]

            # print(page_texts)
            with open("financial_analysis.txt", "w") as outfile:
                outfile.write(page_texts)
            found = 0
            headers = []
            lines = str(page_texts).strip().split('\n')
            last_one = []


            for line in lines:
                split_text = line.split("  ")
                head = []
                if ' Units' in split_text:
                    found = 1
                    simple = []
                    for txt in split_text:
                        if txt != '':
                            simple.append(txt)
                    empty_count = 5
                    key = []
                    if last_one != []:
                        last_one[-1]
                        count = 0
                        for d in last_one[-1]:
                            if d == '':
                                count+=1
                                if count == empty_count:
                                    key.append('')
                                    count=0
                            else:
                                key.append(d)
                                count=0
                        last_one=[]
                        # print(len(key), key)
                        head.append(simple[0])
                        head.append(simple[1])
                        head.append(simple[2])
                        head.append(simple[3])
                        head.append(simple[4])
                        head.append(simple[5])
                        head.append(key[-11]+simple[6])
                        head.append(key[-10]+simple[7])
                        head.append(key[-8]+simple[8])
                        head.append(key[-3]+simple[9])
                        head.append(key[-1]+simple[10])

                    headers.append(head)
                    
                elif ' Income' in split_text:
                    found = 2
                    simple = [0]
                    for txt in split_text:
                        if txt != '':
                            simple.append(txt)
                    if simple[0] == 0:
                        simple = simple[1:]
                    empty_count = 5
                    key = []
                    key1 = []
                    if last_one != []:
                        count = 0
                        for d in last_one[-2]:
                            if d == '':
                                count+=1
                                if count == empty_count:
                                    key.append('')
                                    count=0
                            else:
                                key.append(d)
                                count=0
                        for d in last_one[-1]:
                            if d == '':
                                count+=1
                                if count == empty_count:
                                    key1.append('')
                                    count=0
                            else:
                                key1.append(d)
                                count=0
                        last_one=[]
                        head.append(simple[0])
                        head.append(f'{key1[-8]} {simple[1]}')
                        head.append(f'{key[-8]} {key1[-6]} {simple[2]}')
                        head.append(f'{key[-6]} {key1[-4]} {simple[3]}')
                        head.append(f'{key[-4]} {key1[-3]} {simple[4]}')
                        head.append(f'{key[-1]} {key1[-1]} {simple[5]}')
                    headers = []
                    headers.append(head)
                elif ' Expenses' in split_text:
                    found = 3
                    simple = [0]
                    for txt in split_text:
                        if txt != '':
                            simple.append(txt)
                    if simple[0] == 0:
                        simple = simple[1:]
                    empty_count = 5
                    key = []
                    key1 = []
                    if last_one != []:
                        count = 0
                        for d in last_one[-2]:
                            if d == '':
                                count+=1
                                if count == empty_count:
                                    key.append('')
                                    count=0
                            else:
                                key.append(d)
                                count=0
                        for d in last_one[-1]:
                            if d == '':
                                count+=1
                                if count == empty_count:
                                    key1.append('')
                                    count=0
                            else:
                                key1.append(d)
                                count=0
                        last_one=[]
                        head.append(simple[0])
                        head.append(simple[1])
                        head.append(f'{key1[-9]} {simple[2]}')
                        head.append(f'{key[-8]} {key1[-7]} {simple[3]}')
                        head.append(f'{key[-6]} {key1[-5]} {simple[4]}')
                        head.append(f'{key[-4]} {key1[-3]} {simple[5]}')
                        head.append(f'{key[-1]} {key1[-1]} {simple[6]}')
                    headers = []
                    headers.append(head)
                else:
                    last_one.append(split_text)

                if found == 1:
                    simple=[]
                    for txt in split_text:
                        if txt != '':
                            if ' Meadows' in txt:
                                pass
                            elif 'Martin' in txt:
                                simple.append('')
                                t = txt.split(' ')
                                simple.append(t[-1])
                            else:
                                simple.append(txt)
                    if len(simple)==len(headers[0]):
                        data = {}
                        for field in range(len(headers[0])):
                            data[headers[0][field]] = simple[field]
                        all_data.append(data)

                if found == 2:
                    simple=[]
                    for txt in split_text:
                        if txt != '':
                            simple.append(txt)
                    if len(simple) == 7:
                        old = simple
                        simple = []
                        simple.append(f'{old[0]} {old[1]}')
                        simple.append(old[2])
                        simple.append(old[3])
                        simple.append(old[4])
                        simple.append(old[5])
                        simple.append(old[6])
                    if len(simple)<len(headers[0]):
                        differ = len(headers[0])-len(simple)
                        for i in range(differ):
                            simple.append('')
                    if len(simple)==len(headers[0]):
                        data = {}
                        for field in range(len(headers[0])):
                            data[headers[0][field]] = simple[field]
                        all_data.append(data)

                if found == 3:
                    simple=[]
                    for txt in split_text:
                        if txt != '':
                            simple.append(txt)
                    if len(simple) == 8:
                        old = simple
                        simple = []
                        simple.append(f'{old[0]} {old[1]}')
                        simple.append(old[2])
                        simple.append(old[3])
                        simple.append(old[4])
                        simple.append(old[5])
                        simple.append(old[6])
                        simple.append(old[7])
                    if len(simple)<len(headers[0]) and len(simple)!=1:
                        differ = len(headers[0])-len(simple)
                        for i in range(differ):
                            simple.insert(0, '')
                    if len(simple)==len(headers[0]):
                        data = {}
                        for field in range(len(headers[0])):
                            data[headers[0][field]] = simple[field]
                        all_data.append(data)

            page_texts = pdf[29]
            income_assumption = {}
            expense_assumption = {}
            lines = str(page_texts).strip().split('\n')
            count = 0
            key = []
            vl = []
            store = ''
            for line in lines:
                string = []
                if 'INCOME' in line:
                    count = 1
                if 'EXPENSE' in line:
                    count = 2
                if count==1:
                    split_string= line.split("   ")
                    for txt in split_string:
                        if txt != '':
                            string.append(txt)
                    if len(string) == 2:
                        income_assumption[string[0]] = string[1]
                    if len(string) == 1:
                        if '•' in string[0]:
                            key.append(string[0])
                        else:
                            vl.append(string[0])
                if count == 2:
                    split_string= line.split("   ")
                    for txt in split_string:
                        if txt != '':
                            string.append(txt)
                    if len(string) == 2:
                        if store != '':
                            expense_assumption[string[0]] = f'{store} {string[1]}'
                            store = ''
                        else:
                            expense_assumption[string[0]] = string[1]
                    if len(string) == 1:
                        store = string[0]
            income_assumption[key[0]] = f'{vl[1]} {vl[2]}'
            income_assumption[key[1]] = f'{vl[3]} {vl[4]}'
            if store != '':
                first_key = next(iter(expense_assumption))
                new = expense_assumption[first_key]+' '+store
                expense_assumption[first_key] = new
            all_data.append(income_assumption)
            all_data.append(expense_assumption)

            page_texts = pdf[30]

            with open("sample1.txt", "w") as outfile:
                outfile.write(page_texts)

            existing_loan = {}
            keys = []
            values = []
            lines = str(page_texts).strip().split('\n')
            count = 0
            for line in lines:
                string = []
                if 'Lender' in line:
                    count = 1
                if count>0:
                    split_string= line.split("   ")
                    for txt in split_string:
                        if txt != '':
                            string.append(txt)
                    values.append(string)
            stored_value = ''
            key = []
            vl = []
            for val in values:
                if len(val) == 4:
                    existing_loan[val[0]] = val[1]
                    existing_loan[val[2]] = val[3]
                if len(val) == 2:
                    existing_loan[val[0]] = val[1]
                if len(val) == 3:
                    existing_loan[val[0]] = val[1]
                    if ":" in val[2]:
                        key.append(val[2])
                    else:
                        vl.append(val[2])
                if len(val) == 1:
                    if ':' in val[0]:
                        key.append(val[0])
                    else:
                        vl.append(val[0])
            existing_loan[key[0]] = f"{vl[0]} {vl[1]}"
            existing_loan[f'{vl[2]}{key[1]}'] = vl[3]
            existing_loan[f'{vl[4]} {key[2]}'] = vl[5]
            all_data.append(existing_loan)

            json_data = json.dumps(all_data, indent=4)
            # Save the JSON data to a file
            with open(f"meadow.json", "w") as json_file:
                json_file.write(json_data)
        elif spotted_key == 'TRAVIS':
            with open(pdf_path, "rb") as f:
                pdf = pdftotext.PDF(f)

            all_text = ""
            with pdfplumber.open(pdf_path) as pdf:
                        for page in pdf.pages:
                            text = page.extract_text()
                            all_text += '\n' + text

            all_lines = list(filter(bool, all_text.split('\n')))
            for index, val in enumerate(all_lines):
                    if 'Gross Potential Rent Growth' in val.strip():
                        legend = index
                    if 'FY1/ UNIT ACQUISITION' in val.strip():
                        method = index
            dict2 ={}
            def getSubstringBetweenTwoChars(ch1,ch2,str):
                            return s[s.find(ch1)+len(ch1):s.find(ch2)]

            legen = str(all_lines[legend:method+1])
            s = legen

            dict2["Gross Potential Rent Growth"]= getSubstringBetweenTwoChars('Gross Potential Rent Growth','Loss to Lease 9.0% 8.0% 7.0% 6.0% 5.0%',s).replace("', '","")
            dict2["Loss to Lease "]= getSubstringBetweenTwoChars('Loss to Lease','Vacancy 7.0% 6.0% 5.0% 4.0% 4.0%',s).replace("', '","")
            dict2["Vacancy "]= getSubstringBetweenTwoChars('Vacancy','Model/Admin Units',s).replace("', '","")
            dict2["Model/Admin Units "]= getSubstringBetweenTwoChars('Model/Admin Units','Other Rent Loss',s).replace("', '","")
            dict2["Other Rent Loss "]= getSubstringBetweenTwoChars('Other Rent Loss','Total Economic Loss',s).replace("Gross Potential Rent', '","")
            dict2["Total Economic Loss "]= getSubstringBetweenTwoChars('Total Economic Loss','Other/Utility Reimbursement Income Growth',s).replace("GPR reflects Year 1 Market Rent', '","")
            dict2["Other/Utility Reimbursement Income Growth "]= getSubstringBetweenTwoChars('Other/Utility Reimbursement Income Growth','Operating Expense Growth',s).replace("of $1,254/unit.', '","")
            dict2["Operating Expense Growth "]= getSubstringBetweenTwoChars('Operating Expense Growth','Real Estate Tax Growth',s).replace("', '","")
            dict2["Real Estate Tax Growth "]= getSubstringBetweenTwoChars('Real Estate Tax Growth','FY1/ UNIT ACQUISITION',s).replace("Total Economic Loss', '","")


            output_text_file_path = "page411.txt"
            with open(pdf_path, "rb") as f:
                pdf = pdftotext.PDF(f)
            page_number = 41
            page_text = pdf[page_number - 1]
            page_text_lines = page_text.strip().split('\n')
            table1 = '\n'.join(page_text_lines[11:][:-1])
            with open(output_text_file_path, 'w', encoding='utf-8') as text_file:
                text_file.write(table1)
                
            with open('page411.txt') as csvfile:
                    filereader = csv.reader(csvfile, delimiter="\t")

                    data12 = []
                    table_dict5 = {}
                    for row in filereader:
                        row = [elem for elem in row if elem]
                        b = str(row).replace("  ","-")
                        test_string_parts = b.split('-')
                        test_string_parts = [part.strip() for part in test_string_parts if part != '']
                        d = '- '.join(test_string_parts)
                        e = d.split("-")
                        if e[0] == "":
                            e[0], e[1] = e[1], e[0]
                        data12.append(e)
                    table1_mapping = {
                1: 'Gross Potential Rent',
                2: 'Less: Loss to Lease',
                3: 'Less: Vacancy',
                4: 'Less: Model/Admin Unit',
                5: 'Less: Other Rent Loss',
                7: 'Economic Occupancy',
                9: 'Net Rental Income',
                10: 'Utility Reimbursement Income',
                12: 'Other Income',
                14: 'Gross Revenues',
                15: 'Monthly Revenue',
                16: '% Increase Over Previous Year',

            }
                    for i in range(16):
                        val1 = data12[i]
                        print("data12[i]", data12[i])
                        dict4 = {}
                        for month, value in zip(['FY1/ UNIT ACQUISITION', 'YEAR 1', 'YEAR 2', 'YEAR 3', 'YEAR 4', 'YEAR 5'], val1[1:]):
                            dict4[month] = value

                        table_name = table1_mapping.get(i + 1, f'Table {i + 1}')
                        if table_name not in ["Table 11", "Table 13", "Table 6", "Table 8"]:
                            table_dict5[table_name] = dict4


            with open(pdf_path, "rb") as f:
                pdf = pdftotext.PDF(f)
            page_number = 41
            page_text = pdf[page_number - 1]
            page_text_lines = page_text.strip().split('\n')
            table1 = '\n'.join(page_text_lines[28:][:-1])
            with open("page412.txt", 'w', encoding='utf-8') as text_file:
                text_file.write(table1)
            with open('page412.txt') as csvfile:
                    filereader = csv.reader(csvfile, delimiter="\t")
                    data12 = []
                    table_dict6 = {}
                    for row in filereader:
                        
                        row = [elem for elem in row if elem]
                        b = str(row).replace("  ","-")
                        test_string_parts = b.split('-')
                        test_string_parts = [part.strip() for part in test_string_parts if part != '']
                        d = '- '.join(test_string_parts)
                        e = d.split("-")
                        if e[0] == "":
                            e[0], e[1] = e[1], e[0]
                        data12.append(e)
                    table2_mapping = {
                1: 'Contract Services',
                2: 'Repairs & Maintenance',
                3: 'Make-Ready/Turnover',
                5: 'Administrative',
                7: 'Marketing',
                8: 'Payroll',
                10: 'Utilities',
                11: 'Management Fees',
                12: 'Insurance',
                13: 'Real Estate Taxes',
                14: 'Recurring Capital Expenditures',
                15: 'Total Operating Expenses',
                17: 'Net Operating Income',

            }
                    for i in range(17):
                        val1 = data12[i]
                        dict4 = {}
                        for month, value in zip(['FY1/ UNIT ACQUISITION', 'YEAR 1', 'YEAR 2', 'YEAR 3', 'YEAR 4', 'YEAR 5'], val1[1:]):
                            if value.strip() == "      -":
                                value = "-"
                            dict4[month] = value
                        table_name = table2_mapping.get(i + 1, f'Table {i + 1}')
                        
                        if table_name not in ["Table 16", "Table 4", "Table 6", "Table 9"]:
                            table_dict6[table_name] = dict4

            with open(pdf_path, "rb") as f:
                pdf = pdftotext.PDF(f)
            pdftotext_text = "\n\n".join(pdf)
            page_number = 42
            page_text = pdf[page_number - 1]
            page_text_lines = page_text.strip().split('\n')
            table13 = '\n'.join(page_text_lines[2:])
            with open("tdata2.txt", 'w', encoding='utf-8') as text_file:
                    text_file.write(table13)

            with open('tdata2.txt') as csvfile:
                    filereader = csv.reader(csvfile, delimiter="\t")

                    data12 = []
                    table_dict = {}
                    for row in filereader:
                        
                        row = [elem for elem in row if elem]
                        b = str(row).replace("  ","-")
                        test_string_parts = b.split('-')
                        test_string_parts = [part.strip() for part in test_string_parts if part != '']
                        d = '- '.join(test_string_parts)
                        e = d.split("-")
                        if e[0] == "":
                            e[0], e[1] = e[1], e[0]
                        data12.append(e)
                    table_mapping = {
                1: 'Market Rent',
                2: 'Less: Loss to Lease/Gain to Lease',
                3: 'Gross Potential Rent',
                4: 'Vacancy',
                5: 'Model/Admin Unit',
                6: 'Concessions',
                7: 'Bad Debt/Other Rent Loss',
                8: 'Net Rental Income',
                9: 'Physical Occupancy',
                10: 'Economic Occupancy',
                11: 'Utility Reimbursement Income',
                12: 'Electric',
                13: 'Water/Sewer',
                14: 'Gas',
                15: 'Trash',
                16: 'Pest',
                17: 'Other',
                18: 'Other Income',
                19: 'Misc Income',
                20: 'Admin Fee',
                21: 'MTM Fee',
                22: 'Risk Fee',
                23: 'App Fees',
                24: 'Pet Fee',
                25: 'Damages',
                26: 'Late Fees',
                27: 'Gross Revenues',
            }
                    for i in range(27):
                        val1 = data12[i]
                        dict4 = {}
                        for month, value in zip(['JUL-22', 'AUG-22', 'SEP-22', 'OCT-22', 'NOV-22', 'DEC-22', 'JAN-23', 'FEB-23', 'MAR-23', 'APR-23', 'MAY-23', 'JUN-23'], val1[1:]):
                            if value.strip() == "      -":
                                value = "-"
                            dict4[month] = value
                        table_name = table_mapping.get(i + 1, f'Table {i + 1}')
                        table_dict[table_name] = dict4
                        
            with open(pdf_path, "rb") as f:
                pdf = pdftotext.PDF(f)
            page_number = 42
            page_text = pdf[page_number - 1]
            page_text_lines = page_text.strip().split('\n')
            table14 = '\n'.join(page_text_lines[30:])
            with open("tdata42.txt", 'w', encoding='utf-8') as text_file:
                    text_file.write(table14)

            with open('tdata42.txt') as csvfile:
                    filereader = csv.reader(csvfile, delimiter="\t")

                    data12 = []
                    table_dict1 = {}
                    for row in filereader:
                        
                        row = [elem for elem in row if elem]
                        b = str(row).replace("  ","-")
                        test_string_parts = b.split('-')
                        test_string_parts = [part.strip() for part in test_string_parts if part != '']
                        d = '- '.join(test_string_parts)
                        e = d.split("-")
                        data12.append(e)
                    table_mapping1 = {
                        1: 'Contract Services',
                        5: 'Repairs & Maintenance',
                        3: 'Make-Ready/Turnover',
                        4: 'Administrative',
                        5: 'Marketing',
                        6: 'Payroll',
                        7: 'Controllable Exp Subtotal',
                        8: 'Utilities',
                        9: 'Electric - Common Area',
                        10: 'Water/Sewer',
                        11: 'Gas',
                        12: 'Trash',
                        13: 'Pest',
                        14: 'Other',
                        15: 'Management Fees',
                        16: 'Insurance',
                        17: 'Real Estate Taxes',
                        18: 'Operating Expenses',
                        19: 'Total Expenses',
                        20: 'Net Operating Income',
                        
                    }
                    for i in range(20):
                        val1 = data12[i]
                        dict5 = {}
                        for month, value in zip(['JUL-22', 'AUG-22', 'SEP-22', 'OCT-22', 'NOV-22', 'DEC-22', 'JAN-23', 'FEB-23', 'MAR-23', 'APR-23', 'MAY-23', 'JUN-23'], val1[1:]):
                            if value.strip() == "      -":
                                value = "-"
                            dict5[month] = value
                        table_name = table_mapping1.get(i + 1, f'Table {i + 1}')
                        table_dict1[table_name] = dict5
                        
            with open(pdf_path, "rb") as f:
                pdf = pdftotext.PDF(f)
            pdftotext_text = "\n\n".join(pdf)
            page_number = 43
            page_text = pdf[page_number - 1]
            page_text_lines = page_text.strip().split('\n')
            table43 = '\n'.join(page_text_lines[4:])
            with open("tdata43.txt", 'w', encoding='utf-8') as text_file:
                    text_file.write(table43)

            with open('tdata43.txt') as csvfile:
                    filereader = csv.reader(csvfile, delimiter="\t")
                    data12 = []
                    table_dict3 = {}
                    for row in filereader:
                        
                        row = [elem for elem in row if elem]
                        b = str(row).replace("  ","-")
                        test_string_parts = b.split('-')
                        test_string_parts = [part.strip() for part in test_string_parts if part != '']
                        d = '- '.join(test_string_parts)
                        e = d.split("-")
                        if e[0] == "":
                            e[0], e[1] = e[1], e[0]
                        data12.append(e)
                    table_mapping3 = {
                1: 'Market Rent',
                2: 'Less: Loss to Lease/Gain to Lease',
                3: 'Gross Potential Rent',
                4: 'Vacancy',
                5: 'Model/Admin Unit',
                6: 'Concessions',
                7: 'Bad Debt/Other Rent Loss',
                8: 'Net Rental Income',
                9: 'Physical Occupancy',
                10: 'Economic Occupancy',
                11: 'Utility Reimbursement Income',
                12: 'Electric',
                13: 'Water/Sewer',
                14: 'Gas',
                15: 'Trash',
                16: 'Pest',
                17: 'Other',
                18: 'Other Income',
                19: 'Misc Income',
                20: 'Admin Fee',
                21: 'MTM Fee',
                22: 'Risk Fee',
                23: 'App Fees',
                24: 'Pet Fee',
                25: 'Damages',
                26: 'Late Fees',
                27: 'Gross Revenues',
            }
                    for i in range(27):
                        val1 = data12[i]
                        dict6 = {}
                        for month, value in zip(['TRAILING ','12 MONTHS', '6 MTHS INCOME ','ANNUALIZED', '90 DAY INCOME ','ANNUALIZED', '30 DAY INCOME ','ANNUALIZED', 'YEAR 1 PROFORMA ','UNDERWRITING'], val1[1:]):
                            if value.strip() == "      -":
                                value = "-"
                            dict6[month] = value
                        table_name = table_mapping3.get(i + 1, f'Table {i + 1}')
                        table_dict3[table_name] = dict6
                        
                        
            with open(pdf_path, "rb") as f:
                pdf = pdftotext.PDF(f)
            page_number = 42
            page_text = pdf[page_number - 1]
            page_text_lines = page_text.strip().split('\n')
            table14 = '\n'.join(page_text_lines[30:])
            total_dict = {}
            if "Recurring Capital Expenditures" in table14:
                total_dict["Recurring Capital Expenditures:"] = table14.split("Recurring Capital Expenditures")[1].split("\n")[0].strip()
                
                
            if "NOI (w/resv)" in table14:
                total_dict["NOI (w/resv):"] = table14.split("NOI (w/resv)")[1].split("\n")[0].strip()
                

            with open("tdata431.txt", 'w', encoding='utf-8') as text_file:
                    text_file.write(table14)

            with open('tdata431.txt') as csvfile:
                    filereader = csv.reader(csvfile, delimiter="\t")
                    data12 = []
                    table_dict4 = {}
                    for row in filereader:
                        
                        row = [elem for elem in row if elem]
                        b = str(row).replace("  ","-")
                        test_string_parts = b.split('-')
                        test_string_parts = [part.strip() for part in test_string_parts if part != '']
                        d = '- '.join(test_string_parts)
                        e = d.split("-")
                        data12.append(e)
                    table_mapping5 = {
                        1: 'Contract Services',
                        5: 'Repairs & Maintenance',
                        3: 'Make-Ready/Turnover',
                        4: 'Administrative',
                        5: 'Marketing',
                        6: 'Payroll',
                        7: 'Controllable Exp Subtotal',
                        8: 'Utilities',
                        9: 'Electric - Common Area',
                        10: 'Water/Sewer',
                        11: 'Gas',
                        12: 'Trash',
                        13: 'Pest',
                        14: 'Other',
                        15: 'Management Fees',
                        16: 'Insurance',
                        17: 'Real Estate Taxes',
                        18: 'Operating Expenses',
                        19: 'Total Expenses',
                        20: 'Net Operating Income',
                        
                    }
                    for i in range(20):
                        val1 = data12[i]
                        dict7 = {}
                        for month, value in zip(['TRAILING ','12 MONTHS', '6 MTHS INCOME ','ANNUALIZED', '90 DAY INCOME ','ANNUALIZED', '30 DAY INCOME ','ANNUALIZED', 'YEAR 1 PROFORMA ','UNDERWRITING'], val1[1:]):
                            if value.strip() == "      -":
                                value = "-"
                            dict7[month] = value
                        table_name = table_mapping5.get(i + 1, f'Table {i + 1}')
                        table_dict4[table_name] = dict7
                        
                        list1 = []
                        list2 = []
                        list3 = []
                        list11 = []
                        list22 = []
                        list33 = []
                        
                        list1.append(table_dict6)
                        list2.append(table_dict1)
                        list3.append(table_dict4)
                        list11.append(table_dict)
                        list22.append(table_dict5)
                        list33.append(table_dict3)
                        
                        result_dict = {
                            'list1_key': list1,
                            'list2_key': list2,
                            'list3_key': list3
                        }
                        result_dict1 = {
                            'list11_key': list11,
                            'list22_key': list22,
                            'list33_key': list33
                        }
            response_dict ={}
            response_dict["OPERATING EXPENSES"] = result_dict
            response_dict["RENTAL INCOME"] = result_dict1
            response_dict["primary_data"] = dict2
            json_data = json.dumps(response_dict, indent=4)

            # Save the JSON data to a file
            with open(f"travis.json", "w") as json_file:
                json_file.write(json_data)
                   

    if found_key == '':
        pdf_file_path = pdf_path
        page_number = 10
        extract_images_from_pdf(pdf_file_path, page_number, 'uploaded_files')
        keyword_in_image('uploaded_files/', search_keywords)
    return jsonify({"message": "PDF processing completed successfully!"})
    
if __name__ == '__main__':
    app.run(debug=True)