#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" @package docstring
Cronjob emailer script

Reads an HTML page from a Web server and sends it through email

@author Gabriele Tozzi <gabriele@tozzi.eu>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import sys
import re

from optparse import OptionParser

import urllib, urlparse
from HTMLParser import HTMLParser

import smtplib
from email.Utils import COMMASPACE, formatdate, make_msgid
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

class main:

    NAME = 'mailwww'
    VERSION = '0.3'

    def run(self):
        """ Main entry point """

        # Read command line
        usage = "%prog [options] <url> <address> [<address2>] [<address...>]"
        parser = OptionParser(usage=usage, version=self.NAME + ' ' + self.VERSION)
        parser.add_option("-s", "--smtp", dest="smtp",
            help="SMTP server address. Default: localhost",
            default='localhost')
        parser.add_option("-u", "--smtp_user", dest="smtp_user",
            help="Username for SMTP authentication")
        parser.add_option("-p", "--smtp_pass", dest="smtp_pass",
            help="Password for SMTP authentication")
        parser.add_option("-c", "--cc", dest="cc",
            help="Carbon Copy recipient")
        parser.add_option("-f", "--from", dest="sender",
            help="eMail sender. Default: emailer@localhost",
            default="emailer@localhost")
        parser.add_option("-j", "--subject", dest="subject",
            help="eMail Subject. Default: MailWWW Autogenerated Mail",
            default="MailWWW Autogenerated Mail")
        parser.add_option("-n", "--no-css", dest="nocss",
            help="Disable embedding of linked Style Sheets",
            default=False, action="store_true")
        parser.add_option("-m", "--multiple", dest="multiple",
            help="Send multiple emails: one for each recipient (Cc field is ignored)",
            default=False, action="store_true")
        parser.add_option("-v", "--vverbose", dest="verbose",
            help="Show progress information",
            default=False, action="store_true")

        (options, args) = parser.parse_args()
        
        # Parse mandatory arguments
        if len(args) < 2:
            parser.error("unvalid number of arguments")
        dest = []
        i = 0
        for a in args:
            if i == 0:
                url = a
            else:
                dest.append(a)
            i += 1

        # Parse optional arguments
        cc = []
        if options.cc:
            cc.append(options.cc)
        host = options.smtp
        port = 25
        user = options.smtp_user
        pwd = options.smtp_pass
        sender = options.sender
        subject = options.subject
        nocss = options.nocss
        multiple = options.multiple
        verbose = options.verbose

        # Opens URL
        if verbose:
            print 'Fetching url', url
        f = urllib.urlopen(url)
        html = f.read()
        # Search for meta content-type tag, use this encoding when found
        encre = re.compile(r'<meta\s+http-equiv=(?:"|\')Content-Type(?:"|\')\s+content=(?:"|\')([^\'"]*)(?:"|\')\s*/>',
            re.I | re.M)
        match = encre.search(html)
        if match:
            encoding = match.group(1).split('charset=')[-1]
            try:
                html = unicode(html, encoding, errors='replace')
            except LookupError as e:
                encoding = f.headers['content-type'].split('charset=')[-1]
                html = unicode(html, encoding, errors='replace')
        else:
            encoding = f.headers['content-type'].split('charset=')[-1]
            html = unicode(html, encoding, errors='replace')
        if verbose:
            print 'Detected charset:', encoding
        f.close()
        
        # Retrieve linked style sheets
        if not nocss:
            if verbose:
                print 'Fetching Style Sheets...'
            parser = CSSLister(url)
            parser.feed(html)
            parser.close()
            for search, replace in parser.get_replacements():
                html = html.replace(search, replace, 1)
        
        # Prepare mail
        msg = MIMEMultipart()
        msg['Date'] = formatdate(localtime=True)
        msg['Message-ID'] = make_msgid('emailer')
        msg['Subject'] = subject
        msg['From'] = sender

        if cc and not multiple:
            msg['Cc'] = ', '.join(cc)
        msg.preamble = 'This is a milti-part message in MIME format.'
        
        txt = MIMEText(html.encode('utf-8'), 'html', 'utf-8')
        msg.attach(txt)
        
        if not multiple:
            msg['To'] = ', '.join(dest)
        
        # Sends message
        smtp = smtplib.SMTP()
        smtp.connect(host, port)
        if user:
            smtp.login(user, pwd)
        if multiple:
            for d in dest:
                del msg['To']
                msg['To'] = d
                if verbose:
                    print 'Sending mail to:', d
                print msg.as_string()
                smtp.sendmail(sender, d, msg.as_string())
        else:
            if verbose:
                print 'Sending mail to:', dest, 'Cc:', cc
            smtp.sendmail(sender, dest+cc, msg.as_string())
        smtp.quit()


class CSSLister(HTMLParser):
    
    def __init__(self, baseurl):
        (scheme,netloc,path,parameters,query,fragment) = urlparse.urlparse(baseurl)
        self.__baseurl = scheme + '://' + netloc + '/'
        HTMLParser.__init__(self)
    
    def reset(self):
        self.__repl = []
        HTMLParser.reset(self)
    
    def handle_starttag(self, tag, attrs):
        if tag == 'link' and ('rel', 'stylesheet') in attrs:
            # Found new link tag
            for k, v in attrs:
                if k == 'href':
                    # Go get the CSS
                    c = urllib.urlopen(self.__baseurl + v)
                    css = "<style>\n" + c.read() + "</style>\n"
                    c.close()
                    self.__repl.append( (self.get_starttag_text(), css) )
                    break
    
    def handle_endtag(self, data):
        pass
    
    def get_replacements(self):
        return self.__repl

if __name__ == '__main__':
    app = main()
    app.run()
    sys.exit(0)
