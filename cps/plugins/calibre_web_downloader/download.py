import os
from uuid import uuid4
from flask import Blueprint, request
import requests
from cps import logger, render_template, config
from cps.usermanagement import login_required_if_no_ano
from libgen_api import LibgenSearch
import time

download = Blueprint('download', __name__)
log = logger.create()

@download.route("/download", methods=["GET"])
@login_required_if_no_ano
def start_search():
    return render_template.render_title_template('downloader.html')

@download.route("/search_books", methods=["POST"])
# @login_required_if_no_ano
def search_libgen():
    if request.is_json:
        data = request.get_json()
        book = data.get('title')
        author = data.get('author')
        category = data.get('category')

        results, search = getBookOptions(book, author, category)
        return results
    else:
        log.error_or_exception("Request is not JSON")
        log.error_or_exception("Request Data: %s", request.data)
        log.error_or_exception("Request Headers: %s", request.headers)
        return "Error"

@download.route("/download_book", methods=["POST"])
def download_book():
    print("Starting download process")
   
    if request.is_json:
        data = request.get_json()
        print(data)
        search = LibgenSearch()
        download_links = search.resolve_download_links(data.get('book'))

        print(download_links)

        downloadURL = download_links.get('GET')
        print(downloadURL)

    try:
        with requests.get(downloadURL, stream=True) as response:
            response.raise_for_status()
            print("FIRST LAYER")
            titleHeader = response.headers.get('content-disposition')
            filename = getFileNameFromHeader(titleHeader)
            directory = config.config_calibre_download_dir
            file_path = os.path.join(directory, filename)
            print(f"Filename: {filename}")
            print(f"Download directory: {directory}")
            print(f"Full file path: {file_path}")

            if not os.path.exists(directory):
                os.makedirs(directory)
                print(f"Created directory: {directory}")

            print("Starting file write")
            with open(file_path, 'wb') as file:
                print("SECOND LAYER")
                total_size = int(response.headers.get('content-length', 0))
                bytes_downloaded = 0
                start_time = time.time()
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        file.write(chunk)
                        bytes_downloaded += len(chunk)
                        elapsed_time = time.time() - start_time
                        if elapsed_time > 5:  # Log every 5 seconds
                            print(f"Downloaded {bytes_downloaded}/{total_size} bytes")
                            start_time = time.time()
                print("Download loop completed")
                file.flush()
                os.fsync(file.fileno())
            print("File write completed")

    except Exception as error:
        print(f"Error during download or write: {error}")
        return f"Download failed: {error}"

    print("Download try block completed")

    try:
        print("Updating file timestamp")
        with open(file_path, 'a'):
            os.utime(file_path, None)
        print("File timestamp updated")

        print("Setting file permissions")
        os.chmod(file_path, 0o664)
        print(f"File permissions set to: {oct(os.stat(file_path).st_mode)[-3:]}")

    except Exception as error:
        print(f"Error in post-download operations: {error}")
        return f"Post-download operations failed: {error}"

    print("All operations completed successfully")
    return "Successful Download"

def set_file_permissions(file_path):
    try:
        # Method 1: Using os.chmod()
        os.chmod(file_path, 0o664)
        print(f"Permissions set using os.chmod(): {oct(os.stat(file_path).st_mode)[-3:]}")

        # Method 2: Using subprocess (chmod command)
        subprocess.run(['chmod', '664', file_path], check=True)
        print(f"Permissions set using chmod command: {oct(os.stat(file_path).st_mode)[-3:]}")

    except Exception as e:
        print(f"Error setting permissions: {e}")

def getBookOptions(book, author, category):
    search = LibgenSearch(category)

    title_filters = {"Author": author}
    results = search.search_title(f"{book} {author}")

    # print(results)

    return(results, search)

def getFileNameFromHeader(header):
    if not header:
        return None
    fname = None
    if 'filename=' in header:
        fname = header.split('filename=')[-1].strip().strip('"')
        return fname
    
# def downloadBook()