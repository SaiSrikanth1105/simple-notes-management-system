from flask import Flask, redirect, url_for, render_template, request, flash, session, send_file
from otp import genotp
from cmail import send_mail
from stoken import endata, dndata
from werkzeug.utils import secure_filename
import mysql.connector
from io import BytesIO
import datetime
import os
import re
try:
    import flask_excel as excel
except Exception:
    excel = None

# Database connection
mydb = mysql.connector.connect(host='localhost', user='root', password='admin', database='snmprj')

app = Flask(__name__)
# Tell Flask where to save uploaded files
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# This line automatically creates the folder if it gets deleted by accident!
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['SESSION_TYPE'] = 'filesystem'
app.secret_key = 'codegnan123'
if excel:
    excel.init_excel(app)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('uname')
        password = request.form.get('password')
        email = request.form.get('email')
        print(request.form)
        gotp = genotp()
        userdata = {'username': username, 'password': password, 'email': email, 'gotp': gotp, 'otp_time': str(datetime.datetime.now())}
        subject = "OTP for SNM Registration"
        body = f'OTP for SNM APP REGISTRATION {gotp}'
        send_mail(to=email, subject=subject, body=body)
        flash("OTP has sent to your Email Successfully!!")
        return redirect(url_for('otp', pendata=endata(data=userdata)))
    return render_template('register.html')


@app.route('/otp/<pendata>', methods=['GET', 'POST'])
def otp(pendata):
    if request.method == 'POST':
        uotp = request.form.get('otp')
        try:
            ddata = dndata(pendata)
        except Exception as e:
            print(f"Error decoding data: {e}")
            flash('Could not load page')
            return redirect(url_for('register'))
        else:
            otp_time = datetime.datetime.fromisoformat(ddata.get('otp_time'))
            if (datetime.datetime.now() - otp_time).seconds > 300:
                flash('OTP expired. Please register again.')
                return redirect(url_for('register'))
            if str(uotp) == str(ddata.get('gotp')): 
                try:
                    cursor = mydb.cursor(buffered=True)            
                    query = 'INSERT INTO users (useremail, username, password) VALUES (%s, %s, %s)'                
                    values = [ddata.get("email"), ddata.get("username"), ddata.get("password")]               
                    cursor.execute(query, values)
                    mydb.commit()
                    cursor.close() 
                    flash('Registration successful! Please login.')
                    return redirect(url_for('login'))
                except Exception as e:
                    if 'cursor' in locals(): cursor.close()
                    print(f"Database Error: {e}")
                    flash("An error occurred during registration.")
                    return redirect(url_for('register'))
            else:
                # This kicks in if the OTP doesn't match
                flash("Warning!! Entered OTP is Incorrect. Please register again")
                return redirect(url_for('register'))
        finally:
            # Keeping your finally block exactly as it was
            print('OTP code check completed')         
    return render_template('otp.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        uemail = request.form.get('email')
        upassword = request.form.get('password')
        try:
            cursor = mydb.cursor(buffered=True)
            # Use 'useremail' (the name in your DB)
            cursor.execute('select count(useremail) from users where useremail =%s', [uemail])
            count_email = cursor.fetchone()
            print(f"DEBUG: Found {count_email[0]} users for email {uemail}")
        except Exception as e:
            if 'cursor' in locals(): cursor.close()
            print(f'error in fetching user data :{e}')
            flash("Couldn't fetch the page")
            return redirect(url_for('login'))
        else:
            if count_email and count_email[0] == 1:
                cursor.execute('select password from users where useremail =%s', [uemail])
                stored_psd = cursor.fetchone()
                cursor.close()

                if stored_psd:
                    # If fetchone() returned a tuple (e.g. (password,)), extract the value
                    if isinstance(stored_psd, (tuple, list)):
                        stored_val = stored_psd[0]
                    else:
                        stored_val = stored_psd

                    # If the DB returned bytes, decode to string
                    if isinstance(stored_val, (bytes, bytearray)):
                        try:
                            stored_val = stored_val.decode('utf-8')
                        except Exception:
                            stored_val = stored_val.decode(errors='ignore')

                    # Debug: show exact stored and input values (repr) and lengths
                    print(f"DEBUG stored_val repr: {repr(stored_val)} len={len(str(stored_val)) if stored_val is not None else 0}")
                    print(f"DEBUG upassword repr: {repr(upassword)} len={len(str(upassword)) if upassword is not None else 0}")

                    # Normalize stored value: decode bytes handled above; strip null bytes and surrounding whitespace
                    try:
                        stored_val = str(stored_val).rstrip('\x00').strip()
                    except Exception:
                        stored_val = str(stored_val)

                    # Compare as strings to avoid type/tuple mismatches
                    if str(stored_val) == str(upassword):
                        cursor = mydb.cursor(buffered=True)
                        cursor.execute('select username from users where useremail=%s',[uemail])
                        session['username'] = cursor.fetchone()[0]
                        cursor.close()
                        session['useremail'] = uemail
                        print(session)
                        flash('You are in dashboard!!!')
                        return redirect(url_for('dashboard'))
                    else:
                        flash('Password wrong please Check')
                        return redirect(url_for('login'))
            else:
                cursor.close()
                flash('You entered the invalid email. You need to register.')
                return redirect(url_for('register'))
    else:
        if session.get('useremail'):
            return redirect(url_for('dashboard'))
    return render_template('login.html')


@app.route('/logout')
def logout():
    if session.get('useremail'):
        session.clear()
        flash('You have been logged out successfully.')
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if 'useremail' not in session:
        flash("Please login first")
        return redirect(url_for('login'))
    
    cursor = mydb.cursor(buffered=True)
    cursor.execute('select count(*) from users where useremail=%s',[session.get('useremail')])
    user_exists= cursor.fetchone()[0]
    cursor.close()
    if user_exists == 0:
        session.clear()
        flash('Session expired. Please login again')
        return redirect(url_for('login'))
    
    user_email = session['useremail']
    try:
        cursor = mydb.cursor(buffered=True)
        cursor.execute('SELECT username FROM users WHERE useremail = %s', [user_email])
        user_data = cursor.fetchone()
        username = user_data[0] if user_data else "User"
        # Using standardized: title, description, created_at
        cursor.execute('SELECT title, description, created_at FROM notes WHERE useremail = %s', [user_email])
        user_notes = cursor.fetchall()
        notes_count = len(user_notes)
        cursor.execute('SELECT COUNT(*) FROM filedata WHERE useremail=%s',[user_email])
        files_count = cursor.fetchone()[0]
        cursor.close() 
        return render_template('dashboard.html', name = username, notes = user_notes, notes_count = notes_count,files_count=files_count)

    except Exception as e:
        if 'cursor' in locals(): 
            cursor.close()
        print(f"Dashboard Error: {e}")
        flash("Could not load dashboard data")
        return redirect(url_for('login'))

@app.route('/addnotes', methods=['GET', 'POST'])
def addnotes():
    if session.get('useremail'):
        if request.method == 'POST':
            title = request.form.get('title')
            description = request.form.get('description')
            cursor = mydb.cursor(buffered=True)
            # FIX: Changed useremail to user_email
            cursor.execute('insert into notes (title,description,useremail) values(%s,%s,%s)', [title, description, session.get('useremail')])
            mydb.commit()
            cursor.close()
            flash('Notes added successfully')
            return redirect(url_for('dashboard'))
        return render_template('addnotes.html')
    else:
        return redirect(url_for('login'))

@app.route('/viewallnotes', methods=['GET', 'POST'])
def viewallnotes():
    if session.get('useremail'):
        try:
            cursor = mydb.cursor(buffered=True)
            # Using standardized: created_at
            cursor.execute('select n_id, title, created_at from notes where useremail=%s', [session.get('useremail')])
            allnotesdata = cursor.fetchall()
            cursor.close()
        except Exception as e:
            print(f"Error in finding data {e}")
            flash("could not refresh the page")
            return redirect(url_for('dashboard'))
        else:
            return render_template('viewallnotes.html', data=allnotesdata)
    else:
        return redirect(url_for('login'))

@app.route('/viewnotes/<int:nid>', methods=['GET', 'POST'])
def viewnotes(nid):
    if session.get('useremail'):
        cursor = mydb.cursor(buffered=True)
        cursor.execute('select * from notes where n_id=%s and useremail=%s', [nid, session.get('useremail')])
        notedata = cursor.fetchone()
        cursor.close()
        return render_template('viewnotes.html', notedata=notedata)
    else:
        return redirect(url_for('login'))


@app.route('/updatenotes/<nid>', methods=['GET', 'POST'])
def updatenotes(nid):
    if session.get('useremail'):
        if request.method == 'POST':
            title = request.form.get('title')
            description = request.form.get('description')
            cursor = mydb.cursor(buffered=True)
            print(nid)
            print(session.get('useremail'))
            cursor.execute('update notes set title=%s, description=%s where n_id=%s and useremail=%s', [title, description, nid,session.get('useremail')])
            print(cursor.rowcount)
            mydb.commit()
            cursor.close()
            flash(f'Notes with id {nid} updated successfully')
            return redirect(url_for('viewallnotes'))
        else:
            cursor = mydb.cursor(buffered=True)
            cursor.execute('select * from notes where n_id=%s and useremail=%s',[nid, session.get('useremail')])
            stored_ndata = cursor.fetchone()
            cursor.close()
            return render_template('updatenotes.html',stored_ndata=stored_ndata)
    else:
        return redirect(url_for('login'))


@app.route('/deletenotes/<nid>')
def deletenotes(nid):
    if session.get('useremail'):
        cursor = mydb.cursor(buffered=True)
        cursor.execute('DELETE FROM notes WHERE n_id=%s AND useremail=%s', [nid, session.get('useremail')])
        mydb.commit()
        cursor.close()
        flash(f'Notes {nid} deleted successfully')
        return redirect(url_for('viewallnotes'))
    else:
        flash('please login first')
        return redirect(url_for('login'))


@app.route('/fileupload', methods=['GET', 'POST'])
def fileupload():
    if session.get('useremail'):
        if request.method == 'POST':
            file_data = request.files.get('file')
            # IMPROVEMENT 1: Added check for empty filename just in case
            if not file_data or file_data.filename == '':
                flash('No file selected')
                return redirect(url_for('fileupload'))   
            fname = file_data.filename
            # IMPROVEMENT 2: The 60-character safety check we just discussed!
            if len(fname) > 100:
                flash('File name is too long! Please rename it to be under 60 characters.')
                return redirect(url_for('fileupload'))
            fdata = file_data.read()
            try:
                cursor = mydb.cursor(buffered=True)
                cursor.execute('insert into filedata (file_name,f_data,useremail) values(%s,%s,%s)', [fname, fdata, session.get('useremail')])
                mydb.commit()
                cursor.close()
            except Exception as e:
                print(e)
                flash('could not upload file')
                return redirect(url_for('fileupload'))
            else:
                flash('file has been uploaded successfully')
                return redirect(url_for('fileupload'))
        return render_template('uploadfiles.html')
    else:
        flash('please login first')
        return redirect(url_for('login'))

@app.route('/viewfiles')
def viewfiles():
    if not session.get('useremail'):
        return redirect(url_for('login'))
        
    try:
        cursor = mydb.cursor(buffered=True)
        # We only select ID, Name, and Date so the page loads instantly
        cursor.execute('SELECT f_id, file_name, created_at FROM filedata WHERE useremail = %s', (session.get('useremail'),))
        allfiledata = cursor.fetchall()
        cursor.close()
        # Here is the magic link! We name it 'files' for the HTML page
        return render_template('viewallfiles.html', files=allfiledata)
    except Exception as e:
        print(e)
        flash('Could not fetch files.')
        return redirect(url_for('dashboard'))


@app.route('/fileview/<fid>')
def fileview(fid):
    if session.get('useremail'):
        try:
            cursor = mydb.cursor(buffered=True)
            cursor.execute('select file_name,f_data from filedata where f_id=%s and useremail=%s', [fid, session.get('useremail')])
            result = cursor.fetchone()
            cursor.close()
            if not result:
                flash('File not found')
                return redirect(url_for('dashboard'))
            filename, filedata = result
            fileobj = BytesIO(filedata)
            fileobj.seek(0)
            try:
                return send_file(fileobj, download_name=filename, as_attachment=False)
            except TypeError:
                return send_file(fileobj, attachment_filename=filename, as_attachment=False)
        except Exception as e:
            print(e)
            return redirect(url_for('dashboard'))
    else:
        flash('please login first')
        return redirect(url_for('login'))


@app.route('/downloadfile/<fid>')
def downloadfile(fid):
    if session.get('useremail'):
        try:
            cursor = mydb.cursor(buffered=True)
            cursor.execute('select file_name,f_data from filedata where f_id=%s and useremail=%s',(fid, session.get('useremail')))
            result = cursor.fetchone()
            cursor.close()
            if not result:
                flash('File not found')
                return redirect(url_for('dashboard'))
            filename, filedata = result
            fileobj = BytesIO(filedata)
            fileobj.seek(0)
            return send_file(fileobj, download_name=filename, as_attachment=True)
        except Exception as e:
            print(e)
            return redirect(url_for('dashboard'))
    else:
        flash('please login first')
        return redirect(url_for('login'))


@app.route('/deletefile/<fid>')
def deletefile(fid):
    if session.get('useremail'):
        try:
            cursor = mydb.cursor(buffered=True)
            cursor.execute('delete from filedata where f_id=%s and useremail=%s', (fid, session.get('useremail')))
            print(cursor.rowcount)
            mydb.commit()
            cursor.close()
            flash('file deleted')
            return redirect(url_for('viewfiles'))
        except Exception as e:
            print(e)
            return redirect(url_for('dashboard'))
    else:
        flash('please login first')
        return redirect(url_for('login'))


@app.route('/search', methods=['GET', 'POST'])
def search():
    # check login
    if not session.get('useremail'):
        flash('please login first')
        return redirect(url_for('login'))
    if request.method == 'POST':
        s_data = request.form.get('sdata', '').strip()
        # if empty
        if not s_data:
            flash('Search term is empty')
            return redirect(url_for('dashboard'))
        # simple validation
        if not re.match(r'^[A-Za-z0-9\s]+$', s_data):
            flash('Invalid search term')
            return redirect(url_for('dashboard'))
        try:
            cursor = mydb.cursor(buffered=True)
            # search notes
            cursor.execute('select n_id, title, created_at from notes where useremail=%s and title like %s',(session.get('useremail'), f"%{s_data}%"))
            notes_data = cursor.fetchall()
            # search files
            cursor.execute('select f_id, file_name, created_at from filedata where useremail=%s and file_name like %s',(session.get('useremail'), f"%{s_data}%"))
            files_data = cursor.fetchall()
            cursor.close()
            return render_template('dashboard.html',matched_data=notes_data,file_results=files_data)
        except Exception as e:
            print(e)
            flash('something went wrong')
            return redirect(url_for('dashboard'))
    return redirect(url_for('dashboard'))


@app.route('/getexceldata')
def getexceldata():
    if session.get('useremail'):
        if not excel:
            flash('Excel export not available (missing dependency)')
            return redirect(url_for('dashboard'))
        cursor = mydb.cursor(buffered=True)
        cursor.execute('SELECT n_id, title, description, created_at, useremail FROM notes WHERE useremail=%s', [session.get('useremail')])
        notesdata = cursor.fetchall()
        columns = ['Notes ID', 'Title', 'Description', 'Created At', 'User Email']
        array_data = [columns]
        for row in notesdata:
            clean_row = []
            for item in row:
                if isinstance(item, datetime.datetime):
                    clean_row.append(item.strftime('%Y-%m-%d %H:%M:%S'))
                elif isinstance(item, bytes):
                    clean_row.append(item.decode('utf-8'))
                else: 
                    clean_row.append(item)
            array_data.append(clean_row)
        return excel.make_response_from_array(array_data, 'xlsx', filename='Notesdata')
    else:
        flash('please login first')
        return redirect(url_for('login'))

@app.route('/forgotpassword', methods=['GET', 'POST'])
def forgotpassword():
    if request.method == 'POST':
        user_email = request.form.get('email')
        try:
            cursor = mydb.cursor(buffered=True)
            cursor.execute('select count(useremail) from users where useremail=%s', [user_email])
            email_count = cursor.fetchone()
        except Exception as e:
            print(e)
            flash('could not load page')
            return redirect(url_for('index'))
        else:
            if email_count and email_count[0] == 1:
                subject = 'Reset link for SNM Application'
                reset_link = url_for('changepassword', data=endata(data=user_email), _external=True)
                body = f'Password reset link for the SNM app: {reset_link}'
                send_mail(to=user_email, subject=subject, body=body)
                flash('Reset link has been sent to given mail')
                return redirect(url_for('forgotpassword'))
            else:
                flash('please register first')
                return redirect(url_for('index'))
    return render_template('forgot.html')


@app.route('/changepassword', methods=['GET', 'POST'])
def changepassword():
    if not session.get('useremail'):
        flash('Please login first')
        return redirect(url_for('login'))
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        cursor = mydb.cursor(buffered=True)
        cursor.execute('select password from users where useremail=%s',[session.get('useremail')])
        stored_password = cursor.fetchone()
        if stored_password:
            if isinstance(stored_password, (tuple, list)):
                stored_val = stored_password[0]
            else:
                stored_val = stored_password
            if isinstance(stored_val, (bytes, bytearray)):
                try:
                    stored_val = stored_val.decode('utf-8')
                except Exception:
                    stored_val = stored_val.decode(errors='ignore')
            try:
                stored_val = str(stored_val).rstrip('\x00').strip()
            except Exception:
                stored_val = str(stored_val)
            if str(stored_val) != str(current_password):
                flash('Current password is incorrect')
                cursor.close()
                return redirect(url_for('changepassword'))
        if new_password != confirm_password:
            flash('New passwords do not match')
            cursor.close()
            return redirect(url_for('changepassword'))
        cursor.execute('update users set password=%s where useremail=%s',[new_password, session.get('useremail')])
        mydb.commit()
        cursor.close()
        flash('Password changed successfully')
        return redirect(url_for('dashboard'))
    return render_template('changepassword.html')

if __name__ == '__main__':
    app.run(debug=True, use_reloader=True)
