import yagmail
yag = yagmail.SMTP('projectmailbox999@gmail.com','clkn qkdf oblw fito')
receiver= 'pharit.una@student.mahidol.edu'
contents=[

                "MailBox999 OTP : 203217" 
            ]
yag.send(receiver,'Open Box requested',contents)