import os
from flask import Flask, render_template, request, redirect, send_file
from werkzeug.utils import secure_filename
from PIL import Image
from main import saveNewImageName, decodeImage

userOriginalImageFolder = '/Users/phu/secret_images/originalImages' #A folder which store the original images submitted by user
userEncodedImageDownloadFolder = '/Users/phu/secret_images/downloads' #A folder which store the encoded images for the user to download
userDecodeImageFolder = '/Users/phu/secret_images/userImages' #A folder which store image to be decoded for the user

allowedExtensions = {'png', 'jpeg', 'jpg'}
secret = os.urandom(12)

app = Flask(__name__)
app.config['OriginalImageFolder'] = userOriginalImageFolder
app.config['DownloadEncodedImageFolder'] = userEncodedImageDownloadFolder
app.config['DecodeImageFolder'] = userDecodeImageFolder

app.secret_key = secret

@app.route('/', methods = ['GET', 'POST'])
def main():
    return render_template('main.html')

def allowedFile(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowedExtensions

@app.route('/encode', methods=['GET', 'POST'])
def encodeFile():
    if request.method == 'POST':    # check if the post request has the file part
        if 'inputFile' not in request.files: #Check if there is an input image file
            print("Empty file")
            return redirect('/encode')
        encodingFile = request.files['inputFile']
        encodingMessage = request.form['hiddenMessage']
        encodedFileName = request.form['outputFileName']

        if encodingMessage == '': #Check if there is any message
            print("There is no message")
            return redirect('/encode')
        if encodedFileName == '': #Check if there is any output image name
            print("No output image name")
            return redirect('/encode')

        if encodingFile and allowedFile(encodingFile.filename) and allowedFile(encodedFileName):
            secureFileName = secure_filename(encodingFile.filename)
            encodingFile.save(os.path.join(app.config['OriginalImageFolder'], secureFileName))
            imageData = Image.open(encodingFile)
            imageWidth, imageHeight = imageData.size
            imageCharacterLimit = imageHeight * imageWidth
            messageLength = len(encodingMessage)
            myMessageToHide = str(messageLength) + encodingMessage
            if encodingMessage[:1].isdigit() == True:
                print("Message can not start with a number")
            if len(myMessageToHide) > imageCharacterLimit/3:
                print("Message is too long for image size")
                return redirect('/encode')
            savedImageData = saveNewImageName(os.path.join(app.config['OriginalImageFolder'], secureFileName), encodingMessage, encodedFileName)
            if savedImageData == True:
                return redirect('/downloads/' + encodedFileName)
            else:
                savedImageData.save(os.path.join(app.config['DownloadEncodedImageFolder'], encodedFileName))
                return redirect('/downloads/' + encodedFileName)
        else:
            return redirect('/encode')
    return render_template('encode.html')

@app.route('/downloads/<fileName>', methods = ['GET', 'POST'])
def downloads(fileName):
    return render_template('downloads.html', name = fileName)

@app.route('/downloadFile/<downloadFileName>')
def downloadFile(downloadFileName):
    return send_file(os.path.join(app.config['DownloadEncodedImageFolder'], downloadFileName), as_attachment = True, attachment_filename = '')

@app.route('/decode', methods = ['GET', 'POST'])
def decodeFile():
    if request.method == 'POST':
        # check if the post request has the file part
        if 'inputFile' not in request.files:
            print("Empty file")
            return redirect(request.url)
        decodedFile = request.files['inputFile']

        # If the user does not select a file, the browser submits an
        # empty file without a filename.
        if decodedFile.filename == '':
            print("No image selected")
            return redirect(request.url)
        if decodedFile and allowedFile(decodedFile.filename):
            secureFileName = secure_filename(decodedFile.filename)
            decodedFile.save(os.path.join(app.config['DecodeImageFolder'], secureFileName))
            message = decodeImage(os.path.join(app.config['DecodeImageFolder'], decodedFile.filename))
            return result(message)
    return render_template('decode.html')

@app.route('/result', methods = ['GET', 'POST'])
def result(message):
    return render_template('result.html', name = message)