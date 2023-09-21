from flask import Flask, request, jsonify, render_template, send_file
import requests
import fitz  # PyMuPDF
import os
from os import listdir, path
from werkzeug.utils import secure_filename
from PyPDF2 import PdfFileReader, PdfFileWriter
from datetime import datetime
from reportlab.pdfgen import canvas
from io import BytesIO

PDF_FOLDER = r'D:\TDCReview\py-tdc-api\pdf_files'
SOLR_URL = 'http://localhost:8983/solr/tdc_data_core/update?commit=true'
SOLR_FIELD = 'text_field'  # Solr field to store text
PDF_FOLDER = r'D:\TDCReview\py-tdc-api\pdf_files'
MASTER_FILE_FOLDER = r'D:\TDCReview\py-tdc-api\master_files'
app = Flask(__name__)
PORT = 3000  # หรือพอร์ตที่คุณต้องการ

# Endpoint Home
@app.route('/')
def home():
    return render_template('index.html')


# Function to handle file upload for PDF and Master File
def upload_file(folder):
    uploaded_file = request.files['file']
    if uploaded_file.filename != '':
        filename = secure_filename(uploaded_file.filename)
        file_path = os.path.join(folder, filename)
        uploaded_file.save(file_path)
        return file_path
    else:
        return None

# Endpoint to display document information in master_files folder
@app.route('/document_info', methods=['GET'])
def document_info():
    document_infos = []

    # List all PDF files in the specified folder (master_files)
    pdf_files = [file for file in os.listdir(MASTER_FILE_FOLDER) if file.lower().endswith('.pdf')]

    for pdf_file in pdf_files:
        pdf_path = os.path.join(MASTER_FILE_FOLDER, pdf_file)
        # Extract information about the document (e.g., file name, size, modified date)
        file_name = pdf_file
        file_size = os.path.getsize(pdf_path)  # in bytes
        modified_date = datetime.fromtimestamp(os.path.getmtime(pdf_path)).strftime('%Y-%m-%d %H:%M:%S')
        document_info = {
            'File Name': file_name,
            'File Size (bytes)': file_size,
            'Modified Date': modified_date
        }
        document_infos.append(document_info)

    return render_template('info.html', document_infos=document_infos, enumerate=enumerate)
# Endpoint สำหรับดูไฟล์ PDF
@app.route('/view_pdf/<filename>')
def view_pdf(filename):
    pdf_path = os.path.join(MASTER_FILE_FOLDER, filename)
    return send_file(pdf_path, as_attachment=False)
@app.route('/download', methods=['GET'])
def download_file():
    filename = request.args.get('filename')
    # Path to your file
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

    # Serve the file for download
    return send_file(file_path, as_attachment=True)
# Endpoint for uploading a Master File
@app.route('/upload_master', methods=['POST'])
def upload_master():
    master_path = upload_file(MASTER_FILE_FOLDER)
    if master_path:
        return jsonify(message='Master file uploaded successfully', path=master_path)
    else:
        return jsonify(message='No Master file uploaded')

# Endpoint for accessing the Master File upload page
@app.route('/upload_master_page')
def upload_master_page():
    return render_template('upload_master.html')

# Function to extract text from a PDF file
def extract_text_from_pdf(pdf_path):
    text = ""
    pdf_document = fitz.open(pdf_path)
    for page_num in range(pdf_document.page_count):
        page = pdf_document[page_num]
        text += page.get_text()
    pdf_document.close()
    return text

# Function to send data to Solr
def send_to_solr(text):
    headers = {"Content-Type": "application/json"}
    data = {"add": {"doc": {SOLR_FIELD: text}}}
    response = requests.post(SOLR_URL, json=data, headers=headers)
    return response.status_code

# Endpoint for searching documents
@app.route('/search_page')
def search_page():
    return render_template('search.html')

# Endpoint สำหรับเรียก Solr API เพื่อค้นหา
@app.route('/search', methods=['GET'])
def search():
    search_term = request.args.get('text_field')
    solr_url = f'http://localhost:8983/solr/tdc_data_core/select?text_field={search_term}&rows=50&wt=json'
    # solr_url = f'http://localhost:8983/solr/tdc_data_core/select?q={search_term}&rows=50&wt=json'

    try:
        response = requests.get(solr_url)
        response_json = response.json()
        return jsonify(response_json)
    except requests.exceptions.RequestException as e:
        print('Error connecting to Solr:', e)
        return jsonify(error='Internal Server Error'), 500
    


# if __name__ == "__main__":
    # List all PDF files in the specified folder
    pdf_files = [file for file in os.listdir(PDF_FOLDER) if file.lower().endswith('.pdf')]

    for pdf_file in pdf_files:
        pdf_path = os.path.join(PDF_FOLDER, pdf_file)
        extracted_text = extract_text_from_pdf(pdf_path)

        # Print or do something with the extracted text
        print("Extracted text from", pdf_file, ":")
        print(extracted_text)

        # Send the extracted text to Solr
        status_code = send_to_solr(extracted_text)
        print("Solr status code for","UPLOAD SUCCESS", pdf_file, ":", status_code)
        

# Function to add watermark with the current date to a PDF
def add_watermark_with_date(input_pdf_path, output_pdf_path):
    # Create a PDF canvas
    packet = BytesIO()
    can = canvas.Canvas(packet)

    # Set the font and size for the watermark
    can.setFont('Helvetica-Oblique', 80)  # Change to italic font and adjust size if needed
    can.setFillGray(0.5, 0.5)

    # Get the current date
    current_date = datetime.now().strftime('%Y-%m-%d')

    # Add the date as the watermark
    can.drawCentredString(300, 400, current_date)

    # Add "Download from TDC WU" below the date
    can.setFont('Helvetica', 40)
    can.drawCentredString(300, 300, "Download from TDC WU")

    can.save()

    # Move to the beginning of the BytesIO stream
    packet.seek(0)

    # Create a new PDF with the watermark
    existing_pdf = PdfReader(open(input_pdf_path, "rb"))
    output_pdf = PdfWriter()

    for i in range(len(existing_pdf.pages)):
        page = existing_pdf.pages[i]
        page.merge_page(PdfReader(packet).pages[0])
        output_pdf.add_page(page)

    # Write the watermarked PDF to the output path
    with open(output_pdf_path, "wb") as outputStream:
        output_pdf.write(outputStream)


    
# Endpoint for downloading watermarked PDF with a date watermark
@app.route('/download_watermarked_with_date/<filename>', methods=['GET'])
def download_watermarked_with_date(filename):
    original_pdf_path = os.path.join(MASTER_FILE_FOLDER, filename)
    watermarked_pdf_path = os.path.join(PDF_FOLDER, f'watermarked_{filename}')

    if os.path.exists(original_pdf_path):
        add_watermark_with_date(original_pdf_path, watermarked_pdf_path)
        return send_file(watermarked_pdf_path, as_attachment=True)
    else:
        return jsonify(error='Original PDF not found'), 404

    
def process_and_send_to_solr(file_path):
    extract_text = extract_text_from_pdf(file_path)
    print("Extract text from", file_path, ":")
    print(extract_text)
    
    status_code = send_to_solr(extract_text)
    print("Solr Status code for Upload Success", file_path, ":", status_code)

def process_all_master_files():
    master_files = [file for file in os.listdir(MASTER_FILE_FOLDER) if file.lower().endswith('.pdf')]
    
    for master_file in master_files:
        file_path = os.path.join(MASTER_FILE_FOLDER, master_file)
        process_and_send_to_solr(file_path)

@app.route('/process_master_files', methods=['GET'])
def process_master_files():
    process_all_master_files()
    return jsonify({'message': 'Master files processed successfully.'})

if __name__ == "__main__":
    if not os.path.exists(MASTER_FILE_FOLDER):
        os.makedirs(MASTER_FILE_FOLDER)
    master_files = [file for file in os.listdir(MASTER_FILE_FOLDER) if file.lower().endswith('.pdf')]
    
    # for master_files in master_files:
    #     master_files = os.path.join(MASTER_FILE_FOLDER,master_files)
    #     extract_text = extract_text_from_pdf(master_files)
    #     print("Extract text form",master_files, ":")
    #     print(extract_text)
        
    #     status_code = send_to_solr(extract_text)
    #     print("Solr Status code for","Upload Success",master_files,":",status_code)
    # process_all_master_files()
    app.run(port=PORT, debug=True)
    