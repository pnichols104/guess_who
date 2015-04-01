#!/usr/bin/python
# -*- coding: utf-8 -*-

import sqlite3
import urllib
import os
import requests
import re
from StringIO import StringIO

from PIL import Image
from bs4 import BeautifulSoup, element
from pprint import pprint

from auth import username, password

errors = []

testing = False

def get_form_params(session, url):
    page = session.get(url)
    soupped_page = BeautifulSoup(page.content)
    form_build_id = soupped_page.select('input[name="form_build_id"]')[0]['value']
    form_token = soupped_page.select('input[name="form_token"]')
    if form_token:
        return form_build_id, form_token[0].get('value')
    else:
        return form_build_id, None

def login(session, username, password):
    form_build_id = get_form_params(session, "http://gmcw.groupanizer.com")
    payload = {'name': username,
                'pass': password,
                'form_build_id': form_build_id,
                'form_id': "user_login",
                'op': 'Log in'}
    logged_in = session.post("http://gmcw.groupanizer.com/g/dashboard", data=payload)
    cookies = logged_in.cookies
    return cookies

def get_member_data(session, cookies):
    members = []
    url = "http://gmcw.groupanizer.com/g/members/pictures"
    page = session.get(url, cookies=cookies)
    soup = BeautifulSoup(page.content)
    member_lis = soup.findAll("li", {"class" : "member-picture-row"})
    if testing:
        member_lis = member_lis[:5]
    for li in member_lis:
        member_name = li.find("span", {"class" : "member-name"}).span.string
        member_name = reverse_name(member_name)
        picture_url = li.find("img", typeof="foaf:Image")["src"]
        picture_name = get_picture(session, cookies, picture_url, member_name)
        link = li.find("a")["href"]
        members.append((member_name, picture_name, link))
    return members

def get_picture(session, cookies, picture_url, member_name):
    if "default_user" not in picture_url:
        file_name = "{}.jpg".format(member_name.encode('utf-8'))
        path = "/Users/paulnichols/Desktop/chorus members/{}".format(file_name)
        with open(path, "wb") as f:
            f.write(urllib.urlopen(picture_url).read())
    else:
        file_name = "None"
    return file_name

def create_or_open_db(db_filename):
    db_is_new = True #not os.path.exists(db_filename)
    con = sqlite3.connect(db_filename)
    cursor = con.cursor()
    if db_is_new:
        sql = "DROP TABLE IF EXISTS member_data;"
        cursor.execute(sql)
        sql = '''CREATE TABLE member_data(id integer primary key autoincrement, picture_name TEXT, name TEXT, link TEXT);'''
        cursor.execute(sql)
    else:
        print 'Schema exists\n'

    return con

def insert_into_db(con, picture_name, member_name, link):
    try:
        sql = '''INSERT INTO member_data (picture_name, name, link) VALUES (?, ?, ?)'''
        con.cursor().execute(sql, (picture_name, member_name, link))
        con.commit()
    except Exception as e:
        print "ERROR: ", e
        errors.append((picture_name, member_name, link))

def reverse_name(name):
    words = [word.lstrip() for word in name.split(",")]
    words = [words[-1]] + words[:-1]
    name = " ".join(words).replace(",", "")
    return name

def main():
    db_filename = "members.sqlite3"
    con = create_or_open_db(db_filename)
    cur = con.cursor()
    session = requests.session()
    cookies = login(session, username, password)
    member_data = get_member_data(session, cookies)
    if testing:
        member_data = member_data[:5]
    for link in member_data:
        if link[0] != "test":
            insert_into_db(con, link[1], link[0], link[2])
    sql = '''select * from member_data'''
    cur.execute(sql)
    rows = cur.fetchall()
    for row in rows: print row
    con.close()
    if errors: print errors

if __name__ == '__main__':
    main()