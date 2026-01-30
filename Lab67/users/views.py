from django.shortcuts import render, redirect
from django.db import connection, IntegrityError
from django.contrib import messages
import bcrypt
import requests
from .models import Book, UserBook

def landing(request):
    query = request.GET.get('q','')
    books = []
    username = None

    user_id = request.session.get('user_id')
    if user_id:
        with connection.cursor() as cursor:
            cursor.execute("SELECT user_name FROM lab_user WHERE user_id=%s", [user_id])
            row = cursor.fetchone()
            if row:
                username = row[0]

    if query:
        url = f"https://openlibrary.org/search.json?q={query}"
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                for book in data.get('docs', [])[:12]:
                    title = book.get('title')
                    author = ', '.join(book.get('author_name', ['Unknown']))
                    cover_id = book.get('cover_i')
                    cover_url = f"https://covers.openlibrary.org/b/id/{cover_id}-M.jpg" if cover_id else "/static/users/book-placeholder.jpg"

                    work_key = book.get('key')
                    synopsis = ""
                    if work_key:
                        work_url = f"https://openlibrary.org{work_key}.json"
                        try:
                            work_resp = requests.get(work_url, timeout=3)
                            if work_resp.status_code == 200:
                                work_data = work_resp.json()
                                if 'description' in work_data:
                                    if isinstance(work_data['description'], dict):
                                        synopsis = work_data['description'].get('value','')
                                    else:
                                        synopsis = work_data['description']
                        except requests.RequestException:
                            synopsis = ""
                    books.append({
                        'ol_key': work_key,
                        'title': title,
                        'author': author,
                        'cover_url': cover_url,
                        'synopsis': synopsis[:200] + ("..." if len(synopsis) > 200 else "")
                    })
        except requests.RequestException as e:
            print("API request failed:", e)
    logged_in = request.session.get('logged_in', False)
    username = None
    if logged_in:
        user_id = request.session.get('user_id')
        with connection.cursor() as cursor:
            cursor.execute("SELECT user_name FROM lab_user WHERE user_id = %s", [user_id])
            row = cursor.fetchone()
            if row:
                username = row[0]

    return render(request, 'users/landing.html', {
        "books": books,
        "query": query,
        "logged_in": logged_in,
        "username": username
    })

def profile(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect("user:login")

    with connection.cursor() as cursor:
        cursor.execute("SELECT user_name FROM lab_user WHERE user_id=%s", [user_id])
        row = cursor.fetchone()
        username = row[0] if row else "User"

    user_books = UserBook.objects.filter(user_id=user_id)

    return render(request, "users/profile.html", {"username": username, "user_books": user_books})

def login(request):
    if request.method == 'POST':
        identifier = request.POST.get('Email')
        login_pw = request.POST.get('Password')

        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT user_id, password_hash FROM lab_user WHERE email = %s OR user_name = %s",
                [identifier, identifier]
            )
            row = cursor.fetchone()

        if not row:
            return render(request, "users/login.html", {"error": "User with this email/username doesn't exist"})

        user_id, password_hash = row
        if not bcrypt.checkpw(login_pw.encode('utf-8'), password_hash.encode('utf-8')):
            return render(request, "users/login.html", {"error": "Invalid username or password"})

        # Set session
        request.session['user_id'] = user_id
        request.session['logged_in'] = True

        return redirect("user:landing")

    return render(request, "users/login.html")

def signup(request):
    if request.method == 'POST':
        username = request.POST.get('Username','').strip()
        email = request.POST.get('Email')
        password = request.POST.get('Password')

        errors = []

        if ' ' in username:
            errors.append("Username cannot contain spaces.")
        if not is_valid_email(email):
            errors.append("Please enter a valid email.")

        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM lab_user WHERE email = %s", [email])
            if cursor.fetchone():
                errors.append("An account with the email already exists.")
            cursor.execute("SELECT * FROM lab_user WHERE user_name = %s", [username])
            if cursor.fetchone():
                errors.append("Username taken. Try another one.")

        if errors:
            return render(request, "users/signup.html", {"error": errors[0]})

        # Hash password
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO lab_user (user_name, email, password_hash) VALUES (%s,%s,%s)",
                    [username, email, password_hash]
                )
        except IntegrityError:
            return render(request, "users/signup.html", {"error": "An account with the email already exists."})

        return redirect("user:login")

    return render(request, "users/signup.html")


def logout(request):
    request.session.flush()
    return redirect("user:landing")


def add_to_list(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect("user:login")

    if request.method == "POST":
        ol_key = request.POST['ol_key']
        title = request.POST['title']
        author = request.POST['author']
        cover_url = request.POST.get('cover_url', '')
        status = request.POST['status']

        book, _ = Book.objects.get_or_create(
            ol_key=ol_key,
            defaults={'title': title, 'author': author, 'cover_url': cover_url}
        )
        UserBook.objects.update_or_create(
            user_id=user_id,
            book=book,
            defaults={'status': status}
        )

    return redirect(request.META.get('HTTP_REFERER', '/'))


def profile(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect("user:login")

    username = None
    with connection.cursor() as cursor:
        cursor.execute("SELECT user_name FROM lab_user WHERE user_id = %s", [user_id])
        row = cursor.fetchone()
        if row:
            username = row[0]

    user_books = UserBook.objects.filter(user_id=user_id)

    return render(request, "users/profile.html", {
        "user_books": user_books,
        "username": username  
    })

def is_valid_email(identifier):
    if identifier.count("@") != 1:
        return False
    local, domain = identifier.split("@")
    if not local or "." not in domain:
        return False
    if domain.startswith(".") or domain.endswith("."):
        return False
    return True
