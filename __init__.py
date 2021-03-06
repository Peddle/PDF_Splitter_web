from flask import Flask , render_template, request, flash, url_for, redirect, send_from_directory
from werkzeug.utils import secure_filename
import werkzeug.exceptions
import os
import split_pdf # oh yea
import subprocess

#new import for logging
from logging.handlers import RotatingFileHandler
from flask import request, jsonify
from time import strftime

import logging
import traceback


#======================================================
#	APP CONFIGURATION
#======================================================


app = Flask(__name__) #create flask object
app.secret_key = 'secret' #secret cookie key for flash!
MAX_FILE_SIZE = 16 #size in MB

#debug
#app.root_path = os.getcwd()

#production
app.root_path = '/var/www/Fix/Fix'

app.config['UPLOAD_FOLDER'] = str(app.root_path) + "/static/uploaded_files" #save path
file_input_location_relative = "/static/uploaded_files/" # passed to the script that manipulates the pdf 
file_input_location_absolute = "var/www/Fix/Fix/static/uploaded_files/" # passed to the script that manipulates the pdf 

file_output_location_relative = "/static/served_files"
file_output_location_absolute = "/var/www/Fix/Fix/static/served_files/"

app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE * 1024 * 1024
ALLOWED_EXTENSIONS = set(['pdf']) # allowed file extensions

#logger obj
logger = logging.getLogger(__name__)


#=======================================================
# DEFS
#=======================================================

def print_debug_msg(msg):
	print "************************ "+msg

#check the filename is allowed
def allowed_filename(filename):
	return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

#delete the uploaded file once it has been processed
def clear_uploaded_file(uploaded_filename):
	script_path = str(app.root_path)+file_input_location_relative+"delete_pdfs.sh"
	print_debug_msg(uploaded_filename)
	subprocess.call([script_path, uploaded_filename])

#========================================================
#	APP ROUTES
#========================================================


#file uploading
@app.route('/', methods=['GET', 'POST'])
def upload_pdf():
	if request.method == 'POST':
		if 'pdf' in request.files:
			pdf_file = request.files['pdf']
			if not pdf_file.filename == '':
				if pdf_file and allowed_filename(pdf_file.filename):
					filename = secure_filename(pdf_file.filename) # make sure the filename is not dangerous		

					#PRODUCTION
					#production_path = os.path.join(app.root_path, app.config['UPLOAD_FOLDER'])
					pdf_file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
					return redirect(url_for('uploaded_file',filename=filename))	
				else:
					flash("Only PDF's allowed ;)")
					return redirect(url_for('unsuccesful'))
			else:
				flash("No file selected")
				return redirect(url_for('unsuccesful'))
		else:
			flash("Failed to upload")
			return redirect(url_for('unsuccesful'))

	return render_template('upload.html') # if not a post request, show the html for submitting the file



#process pdf, verify successful and then send it to a custom url
@app.route('/uploads/<filename>')
def uploaded_file(filename):
	
	output_filename = split_pdf.process_pdf(filename, file_input_location_absolute, file_output_location_absolute) #use the pdf splitter module to do the work

	if allowed_filename(output_filename):
		return redirect(url_for('serve_file', output_filename=output_filename))
	else:
		flash(output_filename)
		return redirect(url_for('unsuccesful'))
	


#serve the file with the new name as part of the url for
@app.route('/fixed/<output_filename>')
def serve_file(output_filename):
	output_path = app.root_path+file_output_location_relative #get the directory where the file is stored
	uploaded_filename = output_filename[4:]
	clear_uploaded_file(uploaded_filename) # delete the file that was uploaded
	return send_from_directory(output_path, output_filename) #serve the processed file!



@app.route('/unsuccesful')
def unsuccesful():
	return render_template('unsuccesful.html')

@app.route('/succesful')
def succesful():
	return render_template('succesful.html')

@app.route('/error/')
def error():
	return render_template('error.html')


@app.after_request
def after_request(response):

	if response.status_code != 500:
		ts = strftime('[%Y-%b-%d %H:%M]')
		logger.error(ts+" "+request.remote_addr+" "+request.method
         	+" "+request.scheme+" "+request.full_path+" "+response.status)
	return response
		


#====================================================
#	ERROR HANDLING AND LOGGING
#===================================================



# unsure if works or not
@app.errorhandler(werkzeug.exceptions.RequestEntityTooLarge)
def handle_request_too_large(e):
	flash("Terrible error ocurred. Maximum file size is "+str(MAX_FILE_SIZE)+" MB")
	return redirect(url_for('unsuccesful'))


@app.errorhandler(werkzeug.exceptions.BadRequest)
def handle_bad_request(e):
	flash("Terrible error ocurred. (Bad Request)")
	return redirect(url_for('error'))


@app.errorhandler(werkzeug.exceptions.NotFound)
def handle_not_found(e):
	flash("4 0 4")
	return redirect(url_for('error'))



if __name__ == "__main__":
	handler = RotatingFileHandler('app.log', maxBytes=10000, backupCount=3)
	logger.setLevel(logging.DEBUG)
	logger.addHandler(handler)
	app.run()
