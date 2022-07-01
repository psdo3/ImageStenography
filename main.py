#!/usr/bin/env python3
from curses.ascii import isdigit
from datetime import date
import hashlib
import imghdr
from os import path
from pathlib import Path
from re import M
from sqlite3 import Cursor
import sys
import getopt
from PIL import Image
import base64
from Crypto.Cipher import AES
from Crypto import Random
import mysql.connector
import numpy
import time

def pad(message):
	blockSize = 16
	padBlockSize = blockSize - len(message)
	padCharacter = chr(blockSize - len(message) % blockSize)
	paddedMessage = message + padBlockSize * padCharacter
	print(padBlockSize)
	print(padCharacter)
	print(paddedMessage)
	return paddedMessage

def unpad(paddedMessage):
	padSize = len(paddedMessage) - 1
	lastCharacter = paddedMessage[padSize:]
	intCharacter = ord(lastCharacter)
	paddedCode = paddedMessage[:-intCharacter]
	return paddedCode

def encrypt(message, key):
	secretKey = pad(key)
	cipher = AES.new(secretKey, AES.MODE_CBC)
	encryptedMessage = cipher.encrypt(message)
	baseEncoded = str(base64.b64encode(encryptedMessage))
	print(baseEncoded)
	return baseEncoded

def decrypt(encryptedMessage, key):
	secretKey = pad(key).encode()
	base64DecodingMessage = base64.b64decode(encryptedMessage)
	cipher = AES.new(secretKey, AES.MODE_CBC)
	baseEncodedMessage = base64.b64decode(encryptedMessage.encode())
	decrpytedMessage = cipher.decrypt(baseEncodedMessage)
	decodedDecryptedMessage = decrpytedMessage.decode()
	return unpad(decodedDecryptedMessage)

def saveNewImageName(oldImageName, hiddenMessage, newImageName):
	'''
	Save the modified pixels into a new image file
	oldImageName = the old image name
	hiddenMessage = the message you want to hide in the old image file
	newImageName = the new image name
	'''
	oldImageData = Image.open(oldImageName)
	myMessageToHide = secretMessage(hiddenMessage)
	fileExist = checkDatabase(oldImageData, hiddenMessage)
	if fileExist == True: 
		updateImageMessageCounter(oldImageData, hiddenMessage)
		return True
	else: 
		encodeImage(oldImageName, myMessageToHide, hiddenMessage, oldImageData, newImageName)
		return oldImageData
	#oldImageData.save(newImageName, str(newImageName.split(".")[1].upper()))

def secretMessage(hiddenMessage):
	'''
	Make sure that the message does not start with a number
	Then will count the number of letters in the message and add that number to the start of the message
	hiddenMessage = the message to be encoded
	'''
	if hiddenMessage[:1].isdigit() == True:
		print("Message cannot start with a number")
		print("Please enter a valid message")
		sys.exit()
	else:
		messageLength = len(hiddenMessage)
		myMessageToHid = str(messageLength) + hiddenMessage
		return myMessageToHid

def insertImageDB(imageData, imageName, imageSize, imageHeight, imageWidth, imageFileType, message, outputImageName, runTime):
	'''
	Insert the image and all of its data including the secret message into the database
	'''
	connectStenography = mysql.connector.connect(host = '192.168.50.22', user = 'phu',
                                                password = 'Fgfgtgh12@!', database = 'secret_images')
	cursor = connectStenography.cursor()

	addImage = ("INSERT INTO stenography "
            "(imageID, imageName, imageSize, imageHeight, imageWidth, imageFileType, messageLength, message, outputImageFile, runTime, dateSubmittion)"
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)")

	imageMD5 = hashlib.md5(imageData.tobytes()).hexdigest()
	imageInsert = (imageMD5, imageName, imageSize, imageHeight, imageWidth, imageFileType, len(message), message, outputImageName, runTime, date.today())
	cursor.execute(addImage, imageInsert)
	updateImageMessageCounter(imageData, message)
	connectStenography.commit()
	cursor.close()
	connectStenography.close()

def updateImageMessageCounter(imageData, message):
	'''
	Update the database with the number of occurence for each of the image file or message into their respective tables
	'''
	connectStenography = mysql.connector.connect(host = '192.168.50.22', user = 'phu',
                                                password = 'Fgfgtgh12@!', database = 'secret_images')
	cursor = connectStenography.cursor()
	imageMD5 = hashlib.md5(imageData.tobytes()).hexdigest()
	#ImageUpdater
	imageDataSelect = ("SELECT imageIDCount FROM imageDataCount WHERE imageID = %s ")
	imageDataInput = (imageMD5,)
	cursor.execute(imageDataSelect, imageDataInput)
	imageCountResult = cursor.fetchone()
	if(imageCountResult == None):
		imageIDCount = 1
		imageDataCountInitial = ("INSERT INTO imageDataCount (imageID, imageIDCount) VALUES (%s, %s)")
		imageDataInsert = (imageMD5, imageIDCount)
		cursor.execute(imageDataCountInitial, imageDataInsert)
	else:
		imageDataCountUpdate = ("UPDATE imageDataCount SET imageIDCount = imageIDCount + 1 WHERE imageID = %s")
		cursor.execute(imageDataCountUpdate, imageDataInput)
	#MessageUpdater
	messageSelect = ("SELECT messageCount FROM messageCounter WHERE message = %s ")
	messageInput = (message,)
	cursor.execute(messageSelect, messageInput)
	messageCountResult = cursor.fetchone()
	if(messageCountResult == None):
		messageCount = 1
		messageCountInitial = ("INSERT INTO messageCounter (message, messageCount) VALUES (%s, %s)")
		mesageInsert = (message, messageCount)
		cursor.execute(messageCountInitial, mesageInsert)
	else:
		messageCountUpdate = ("UPDATE messageCounter SET messageCount = messageCount + 1 WHERE message = %s")
		cursor.execute(messageCountUpdate, messageInput)
	connectStenography.commit()
	cursor.close()
	connectStenography.close()

def checkDatabase(imageData, message):
	'''
	Checking the database whether the image file and message combination already existed or not
	'''
	connectStenography = mysql.connector.connect(host = '192.168.50.22', user = 'phu',
                                                password = 'Fgfgtgh12@!', database = 'secret_images')
	cursor = connectStenography.cursor(buffered = True)
	imageMD5 = hashlib.md5(imageData.tobytes()).hexdigest()

	checkingIfFileExist = ("SELECT outputImageFile FROM stenography WHERE imageID = %s AND message = %s")
	imageDataMessage = (imageMD5, message)
	cursor.execute(checkingIfFileExist, imageDataMessage)
	imageDataMessageResult = cursor.fetchone()
	if imageDataMessageResult != None:
		print("Image already exist")
		return True
	else:
		print("Image does not exist")
		return False

def encodeImage(oldImageName, myMessageToHide, hiddenMessage, oldImageData, newImageName):
	'''
	Encode the image with the secret message
	'''
	newImageData = oldImageData.copy()
	startTime = time.process_time()
	oldImageExtension = imghdr.what(oldImageName)
	validExtensions = ['jpeg','pdf','png']
	oldImageWidth, oldImageHeight = newImageData.size
	oldImageSize = oldImageHeight * oldImageWidth
	imageCharacterLimit = (oldImageWidth * oldImageHeight) / 3
	x = 0
	y = 0
	counter = 0
	if oldImageName == None:
		print("There is no input, put something in")
		sys.exit()
	if not oldImageExtension in validExtensions:
		print("File not supported!")
		sys.exit()

	else:
		imageRGB = newImageData.convert("RGB")
		if len(myMessageToHide) > imageCharacterLimit:
			print("Size is too big for pixel size")
			sys.exit(2)
		else:
			for character in myMessageToHide:
				binary = format(ord(character), 'b').zfill(8)
				for b in binary:
					if counter > 2:
						counter = 0
						y += 1
					if y > oldImageHeight - 1:
						y = 0
						x += 1
					imageValue = list(imageRGB.getpixel((x,y)))
					if int(b) == 0:
						if imageValue[counter] % 2 == 1:
							imageValue[counter] += 1
					else:
						if imageValue[counter] % 2 == 0:
							imageValue[counter] += 1
					newImageData.putpixel((x, y), tuple(imageValue))
					imageRGB = newImageData.convert("RGB")
					counter += 1
				y += 1
				counter = 0
		endTime = time.process_time()
		runTime = endTime - startTime
		insertImageDB(oldImageData, oldImageName, oldImageSize, oldImageHeight, oldImageWidth, oldImageExtension, hiddenMessage, newImageName, runTime)

def decodeImage(newImageName):
	'''
	Decode the image file and return the secret message
	'''
	newImageData = Image.open(newImageName)
	newImageExtension = imghdr.what(newImageName)
	validExtensions = ['jpeg','pdf','png']
	newImageWidth, newImageHeight = newImageData.size
	x = 0
	y = 0
	counter = 0

	if not newImageExtension in validExtensions:
		print("File not supported!")
		sys.exit()
	else:
		newImageData = Image.open(newImageName)
		imageRGB = newImageData.convert("RGB")
		myNumber = ''
		myDigit = ''
		myMessage = ''
		imageValue = list(imageRGB.getpixel((x,y)))

		if newImageName == None:
			print("There is no input, put something in")
			sys.exit()

		while(True):
			binaryString = ''
			for i in range(3):
				if y >= newImageHeight:
					y = 0
					x += 1
				imageValue = list(imageRGB.getpixel((x,y)))
				for j in range(3):
					if(imageValue[j] % 2 == 0):
						binaryString += '0'
					else:
						binaryString += '1'
				y += 1
			myDigit = chr(int(binaryString[:8],2))
			counter += 1
			if(myDigit.isdigit() == True):
				myNumber += myDigit
			else:
				myMessage += myDigit
			if(counter - len(myNumber) >= int(myNumber)):
				return myMessage

def main():
	try:
		opts, args = getopt.getopt(sys.argv[1:], "e:d:m:c:o:p:")

	except getopt.GetoptError as err:
		print(err)
		sys.exit(2)

	encodingFile = None
	decodingFile = None
	encryptPassword = None
	decryptPassword = None

	for opt, arg in opts:
		if opt in ['-m']:
			myMessageToHide = arg
		if opt in ['-o']:
			newImageName = arg
		if opt in ['-c']:
			encryptPassword = arg
		if opt in ['-e']:
			encodingFile = arg
		if opt in ['-d']:
			decodingFile = arg
			encryptedMessage = decodeImage(decodingFile)
		if opt in ['-p']:
			decryptPassword = arg

	if decodingFile != None:
		if decryptPassword != None:
			decryptMessage = decrypt(encryptedMessage, decryptPassword)
			print(decryptMessage)
		else:
			print(encryptedMessage)
	if encodingFile != None and myMessageToHide != None and newImageName != None:
		if encryptPassword != None:
			encryptMessage = encrypt(myMessageToHide, encryptPassword)
			encryptMessage = secretMessage(encryptMessage)
			saveNewImageName(encodingFile, encryptMessage, newImageName)
		else:
			saveNewImageName(encodingFile, myMessageToHide, newImageName)

main()	