# app.py

import os
import zipfile
import shutil
import xml.etree.ElementTree as ET
from flask import Flask, render_template, request, redirect, url_for, send_from_directory

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
EXTRACT_FOLDER = 'extracted'

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(EXTRACT_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def extract_imscc(file_path, extract_to):
    if os.path.exists(extract_to):
        shutil.rmtree(extract_to)
    with zipfile.ZipFile(file_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)

def parse_manifest(manifest_path):
    tree = ET.parse(manifest_path)
    root = tree.getroot()
    ns = {'ns': root.tag.split('}')[0].strip('{')}
    org = root.find("ns:organizations/ns:organization", ns)

    items = []

    def walk(item, depth=0):
        title_el = item.find("ns:title", ns)
        title = title_el.text if title_el is not None else "Untitled"
        identifierref = item.attrib.get("identifierref")
        items.append({
            'title': title,
            'depth': depth,
            'identifierref': identifierref
        })
        for child in item.findall("ns:item", ns):
            walk(child, depth + 1)

    for item in org.findall("ns:item", ns):
        walk(item)

    return items

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        file = request.files['imscc_file']
        if file and file.filename.endswith('.imscc'):
            filepath = os.path.join(UPLOAD_FOLDER, file.filename)
            file.save(filepath)
            extract_imscc(filepath, EXTRACT_FOLDER)
            return redirect(url_for('view_course'))
    return render_template('index.html')

@app.route('/course')
def view_course():
    manifest_path = os.path.join(EXTRACT_FOLDER, 'imsmanifest.xml')
    if not os.path.exists(manifest_path):
        return "Manifest file not found", 400

    items = parse_manifest(manifest_path)
    return render_template('viewer.html', items=items)

from bs4 import BeautifulSoup

@app.route('/content/<identifierref>')
def view_content(identifierref):
    manifest_path = os.path.join(EXTRACT_FOLDER, 'imsmanifest.xml')
    
    if not os.path.exists(manifest_path):
        return "imsmanifest.xml not found", 404

    try:
        # Parse the manifest XML
        with open(manifest_path, 'r', encoding='utf-8') as f:
            soup = BeautifulSoup(f.read(), 'xml')

        # Look up the resource by identifier
        resource = soup.find('resource', {'identifier': identifierref})
        if not resource:
            return f"No resource found for: {identifierref}", 404

        # Get the href pointing to actual file content
        href = resource.get('href')
        if not href:
            return f"No href found in resource for: {identifierref}", 404

        full_path = os.path.join(EXTRACT_FOLDER, href)

        if not os.path.exists(full_path):
            return f"Content file not found: {href}", 404

        # Load the HTML/text content
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Render content inside a viewer template
        return render_template('content_viewer.html', content=content, filename=href)

    except Exception as e:
        return f"Error while displaying content: {str(e)}", 500


if __name__ == '__main__':
    app.run(debug=True)
