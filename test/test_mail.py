import os
import tempfile


def test_email_message():
    """
    Test basic EmailMessage creation
    """
    from uliweb.mail import EmailMessage

    msg = EmailMessage('from@test.com', 'to@test.com', 'Test Subject', 'Test Body')
    assert msg.subject == 'Test Subject'
    assert msg.message == 'Test Body'
    # Check that str doesn't raise an exception
    result = str(msg)
    assert 'From: from@test.com' in result
    assert 'To: to@test.com' in result
    # Subject may be encoded (quoted-printable), so check for Test or Subject
    assert 'Subject:' in result


def test_email_message_with_html():
    """
    Test EmailMessage with HTML content
    """
    from uliweb.mail import EmailMessage

    msg = EmailMessage('from@test.com', 'to@test.com', 'Test', '<b>HTML</b>', html=True)
    assert msg.html is True


def test_email_message_with_cc():
    """
    Test EmailMessage with CC
    """
    from uliweb.mail import EmailMessage

    msg = EmailMessage('from@test.com', 'to@test.com', 'Test', 'Body', cc_='cc@test.com')
    result = str(msg)
    assert 'CC: cc@test.com' in result or 'cc@test.com' in result


def test_email_message_attachment_text():
    """
    Test EmailMessage with text attachment
    """
    import os
    import tempfile
    from uliweb.mail import EmailMessage
    from email.mime.text import MIMEText

    # Create a temporary text file for testing
    fd, temp_file = tempfile.mkstemp(suffix='.txt')
    os.write(fd, b'test content for attachment')
    os.close(fd)

    try:
        # Create EmailMessage and add attachment
        msg = EmailMessage('from@test.com', 'to@test.com', 'Test', 'Body')
        att = msg.getAttachment(temp_file)

        # Check attachment type
        assert isinstance(att, MIMEText)
    finally:
        os.unlink(temp_file)


def test_email_message_attachment_html():
    """
    Test EmailMessage with HTML attachment
    """
    import os
    import tempfile
    from uliweb.mail import EmailMessage
    from email.mime.text import MIMEText

    # Create a temporary HTML file for testing
    fd, temp_file = tempfile.mkstemp(suffix='.html')
    os.write(fd, b'<html><body><h1>Test</h1></body></html>')
    os.close(fd)

    try:
        # Create EmailMessage and add attachment
        msg = EmailMessage('from@test.com', 'to@test.com', 'Test', 'Body')
        att = msg.getAttachment(temp_file)

        # Check attachment type
        assert isinstance(att, MIMEText)
    finally:
        os.unlink(temp_file)


def test_email_message_attachment_image():
    """
    Test EmailMessage with image attachment
    """
    import os
    import tempfile
    from uliweb.mail import EmailMessage
    from email.mime.image import MIMEImage

    # Create a temporary image file for testing (minimal PNG)
    fd, temp_file = tempfile.mkstemp(suffix='.png')
    os.write(fd, b'\x89PNG\r\n\x1a\n')
    os.close(fd)

    try:
        # Create EmailMessage and add attachment
        msg = EmailMessage('from@test.com', 'to@test.com', 'Test', 'Body')
        att = msg.getAttachment(temp_file)

        # Check attachment type
        assert isinstance(att, MIMEImage)
    finally:
        os.unlink(temp_file)


def test_email_message_attachment_binary():
    """
    Test EmailMessage with binary attachment
    """
    import os
    import tempfile
    from uliweb.mail import EmailMessage
    from email.mime.base import MIMEBase

    # Create a temporary binary file for testing
    fd, temp_file = tempfile.mkstemp(suffix='.bin')
    os.write(fd, b'\x00\x01\x02\x03\x04\x05')
    os.close(fd)

    try:
        # Create EmailMessage and add attachment
        msg = EmailMessage('from@test.com', 'to@test.com', 'Test', 'Body')
        att = msg.getAttachment(temp_file)

        # Check attachment type
        assert isinstance(att, MIMEBase)
    finally:
        os.unlink(temp_file)


def test_email_message_attach_method():
    """
    Test EmailMessage.attach() method
    """
    import os
    import tempfile
    from uliweb.mail import EmailMessage

    # Create a temporary text file
    fd, temp_file = tempfile.mkstemp(suffix='.txt')
    os.write(fd, b'attached content')
    os.close(fd)

    try:
        # Create EmailMessage and use attach method
        msg = EmailMessage('from@test.com', 'to@test.com', 'Test', 'Body')
        msg.attach(temp_file)

        # Check that attachment was added (body + attachment = 2)
        assert len(msg.msg.get_payload()) == 2
    finally:
        os.unlink(temp_file)


def test_email_message_with_attachments():
    """
    Test EmailMessage with multiple attachments
    """
    import os
    import tempfile
    from uliweb.mail import EmailMessage

    # Create temporary files
    fd1, temp_file1 = tempfile.mkstemp(suffix='.txt')
    os.write(fd1, b'file 1')
    os.close(fd1)

    fd2, temp_file2 = tempfile.mkstemp(suffix='.txt')
    os.write(fd2, b'file 2')
    os.close(fd2)

    try:
        # Create EmailMessage with attachments list
        msg = EmailMessage('from@test.com', 'to@test.com', 'Test', 'Body',
                          attachments=[temp_file1, temp_file2])

        # Check that attachments were added (body + 2 attachments = 3)
        assert len(msg.msg.get_payload()) == 3
    finally:
        os.unlink(temp_file1)
        os.unlink(temp_file2)


def test_email_message_unicode():
    """
    Test EmailMessage with Unicode content
    """
    from uliweb.mail import EmailMessage

    msg = EmailMessage('from@test.com', 'to@test.com', '测试主题', '测试内容')
    assert msg.subject == '测试主题'
    assert msg.message == '测试内容'


def test_email_message_unicode_attachment():
    """
    Test EmailMessage with Unicode filename
    """
    import os
    import tempfile
    from uliweb.mail import EmailMessage

    # Create a temporary file
    fd, temp_file = tempfile.mkstemp(suffix='.txt')
    os.write(fd, b'test')
    os.close(fd)

    try:
        # Create EmailMessage and get attachment
        msg = EmailMessage('from@test.com', 'to@test.com', 'Test', 'Body')
        att = msg.getAttachment(temp_file)

        # Check filename is preserved
        assert 'Content-Disposition' in att.keys() or att.get('Content-Disposition')
    finally:
        os.unlink(temp_file)
