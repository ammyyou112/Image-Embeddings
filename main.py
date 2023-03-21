import time
from flask import Flask, request, render_template, send_file, send_from_directory
import os
import zipfile
import io
from io import StringIO
import tqdm
import glob
import traceback
import psycopg2.extras
import pymongo
import gridfs
import bson
import json
from bson.objectid import ObjectId
from multiprocessing.pool import ThreadPool
from embeddings import get_embeddings
from config import config

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = os.path.abspath('uploads')

# initialize PostgreSQL connection and cursor
def connect():
    connection = None
    try:
        params = config()
        print('Connecting to PostgreSQL database')
        connection = psycopg2.connect(**params)

        # create a cursor
        crsr = connection.cursor()

        # create the files table if it doesn't exist
        crsr.execute("CREATE TABLE IF NOT EXISTS files (id SERIAL PRIMARY KEY, filename VARCHAR(255) NOT NULL, path VARCHAR(255) NOT NULL, file_content BYTEA)")

        # commit changes to database
        connection.commit()

        print('PostgreSQL database version: ')
        crsr.execute('Select Version()')
        db_version = crsr.fetchone()
        print(db_version)
        crsr.close()
    except(Exception, psycopg2.DatabaseError) as error:
        print(error)
    finally:
        if connection is not None:
            connection.close()
            print('Database connection terminated')

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if 'file' not in request.files:
            return 'No file part'
        uploaded_file = request.files['file']
        if uploaded_file.filename == '':
            return 'No selected file'

        # extract the uploaded zip file
        zip_path = os.path.join(app.config['UPLOAD_FOLDER'], uploaded_file.filename)
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(app.config['UPLOAD_FOLDER'])

        # create a list of extracted files to show on the webpage
        extracted_dir = os.path.join(app.config['UPLOAD_FOLDER'], os.path.splitext(uploaded_file.filename)[0])
        files = os.listdir(extracted_dir)
        file_names = [os.path.basename(file) for file in files]

        # insert file data into the database
        connection = psycopg2.connect(**config())
        crsr = connection.cursor()

        # create the table if it doesn't exist
        crsr.execute(
            "CREATE TABLE IF NOT EXISTS files (id SERIAL PRIMARY KEY, filename VARCHAR(255) NOT NULL, path VARCHAR(255) NOT NULL, file_content BYTEA)")

        # insert data for each file
        for file_name in file_names:
            file_path = os.path.join(extracted_dir, file_name)
            with open(file_path, 'rb') as f:
                file_content = f.read()
            crsr.execute("INSERT INTO files (filename, path, file_content) VALUES (%s, %s, %s)",
                         (file_name, file_path, file_content))

        connection.commit()
        crsr.close()

        # get the file names and paths from the database
        crsr = connection.cursor()
        crsr.execute("SELECT filename, path FROM files")
        results = crsr.fetchall()
        crsr.close()

        # create a list of dictionaries containing file name and path
        file_list = [{'filename': result[0], 'path': result[1]} for result in results]

        # create a JSON file of the file list
        json_path = os.path.join(app.config['UPLOAD_FOLDER'], 'files.json')
        with open(json_path, 'w') as f:
            json.dump(file_list, f)

        # perform file search if search term is provided
        search_term = request.form.get('search')
        if search_term and search_term.strip():
            matched_files = []
            connection = psycopg2.connect(**config())
            crsr = connection.cursor()
            crsr.execute("SELECT id, filename, path FROM files WHERE filename LIKE %s", (f'%{search_term}%',))
            results = crsr.fetchall()
            crsr.close()
            for result in results:
                matched_files.append(os.path.join(extracted_dir, result[1]))
            if matched_files:
                return render_template('files.html', files=matched_files)
            else:
                return 'File not found'
        else:
            files = [os.path.join(extracted_dir, file_name) for file_name in file_names]
            return render_template('files.html', files=files)
    else:
        return render_template('index.html')


@app.route('/uploads/<filename>')
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


@app.route('/file/<path:filename>')
def file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


@app.route('/image/<path:filename>')
def image(filename):
    return render_template('image.html', filename=filename)


if __name__ == '__main__':
    connect()
    app.run(debug=True)
