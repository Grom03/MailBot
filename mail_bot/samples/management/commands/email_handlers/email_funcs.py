import imaplib
import email
import email.message


def get_mail_server(login, password, host, port):
    try:
        mail = imaplib.IMAP4_SSL(host, port)
        mail.login(login, password)
        mail.select('INBOX')
        return mail
    except imaplib.IMAP4_SSL.error:
        return None


def get_unseen_mails(mail, mails_number):
    _, data = mail.search(None, "UNSEEN")

    ids = data[0]
    id_list = ids.split()

    if len(id_list) < mails_number:
        mails_number = len(id_list)

    email_bodies = []

    for i in range(1, mails_number + 1):
        _, data = mail.fetch(id_list[-i], "(RFC822)")
        raw_email = data[0][1]
        raw_email_string = raw_email.decode('utf-8')

        email_message = email.message_from_string(raw_email_string)

        body = email_message.get_payload(decode=True).decode('utf-8')
        email_bodies.append(body)

    return email_bodies
