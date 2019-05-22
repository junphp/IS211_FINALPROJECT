
CREATE TABLE IF NOT EXISTS blog_user (
    userid INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT, email TEXT,
    password TEXT,
    logged_in NUMERIC
);

CREATE TABLE IF NOT EXISTS post (
    postid INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    content TEXT,
    date_posted TEXT,
    auth_id TEXT,
    auth_name TEXT,
    cat TEXT,
    stat_post TEXT DEFAULT 'p'
);


CREATE TABLE IF NOT EXISTS category (
    catid INTEGER PRIMARY KEY AUTOINCREMENT,
    cat TEXT
);