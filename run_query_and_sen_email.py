%pip install pandas
%pip install secure-smtplib

import pandas as pd
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import os

# Function to run a query and return a DataFrame
def run_query(query):
    # Your code to run the query and fetch the data
    # For example:
    # result = spark.sql(query)
    # return result.toPandas()

# Sample query
query = "SELECT * FROM your_table"

# Run the query and get the result as a DataFrame
data = run_query(query)

# Create an Excel file from the DataFrame
file_path = "/dbfs/tmp/output.xlsx"  # Use an appropriate file path
data.to_excel(file_path, index=False)

# Email configuration
email_from = "your_email@example.com"
email_to = "recipient_email@example.com"
email_subject = "Data Export"
email_body = "Please find the attached Excel file."

# Send email with the Excel file attached
msg = MIMEMultipart()
msg['From'] = email_from
msg['To'] = email_to
msg['Subject'] = email_subject
msg.attach(MIMEText(email_body, 'plain'))

attachment = open(file_path, "rb")
part = MIMEBase('application', 'octet-stream')
part.set_payload((attachment).read())
encoders.encode_base64(part)
part.add_header('Content-Disposition', "attachment; filename= %s" % os.path.basename(file_path))
msg.attach(part)

server = smtplib.SMTP('smtp.example.com', 587)  # Use your SMTP server
server.starttls()
server.login(email_from, "your_password")  # Use your email password
server.sendmail(email_from, email_to, msg.as_string())
server.quit()

# Remove the temporary Excel file
os.remove(file_path)
