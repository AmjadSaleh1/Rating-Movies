from flask import Flask, render_template, redirect, url_for, request
from flask_bootstrap import Bootstrap5
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Float, desc
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired
import requests

MOVIE_API = '54561d1f5f99a409c5b40ae99cee493d'
API_URL = 'https://api.themoviedb.org/3/search/movie'
MOVIE_ID_EP = 'https://api.themoviedb.org/3/movie/'


class MyForm(FlaskForm):
    rating = StringField(label='Enter Your rating out of 10', validators=[DataRequired()])
    review = StringField(label='review', validators=[DataRequired()])
    done = SubmitField(label='Done')


class SearchForm(FlaskForm):
    movie_name = StringField(label='Movie Title', validators=[DataRequired()])
    add = SubmitField(label='Search Movie')


app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
Bootstrap5(app)


class Base(DeclarativeBase):
    pass


app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///movies.db'
db = SQLAlchemy(model_class=Base)
db.init_app(app)


class Movie(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(250), unique=True, nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(String(250))
    rating: Mapped[float] = mapped_column(Float)
    ranking: Mapped[int] = mapped_column(Integer, nullable=True)
    review: Mapped[str] = mapped_column(String(250))
    img_url: Mapped[str] = mapped_column(String(250))


with app.app_context():
    db.create_all()


@app.route("/")
def home():
    with app.app_context():
        # Fetch movies ordered by rating descending
        result = db.session.execute(db.select(Movie).order_by(Movie.rating.desc()))
        all_movies = result.scalars().all()

        # Update rankings
        for index, movie in enumerate(all_movies, start=1):
            movie.ranking = index  # Update ranking directly on instance

        # Commit updated rankings
        db.session.commit()

        # Fetch updated movies to ensure session is active and bound
        updated_result = db.session.execute(db.select(Movie).order_by(Movie.ranking))
        updated_movies = updated_result.scalars().all()

    return render_template("index.html", movies=all_movies)


@app.route("/edit", methods=["GET", "POST"])
def edit():
    form = MyForm()
    movie_id = request.args.get("id")
    movie = db.get_or_404(Movie, movie_id)
    if form.validate_on_submit():
        movie.rating = float(form.rating.data)
        movie.review = form.review.data
        db.session.commit()
        return redirect(url_for('home'))
    return render_template("edit.html", movie=movie, form=form)


@app.route("/delete", methods=["GET", "POST"])
def delete():
    movie_id = request.args.get("id")
    movie = db.session.execute(db.select(Movie).where(Movie.id == movie_id)).scalar()
    db.session.delete(movie)
    db.session.commit()
    return redirect(url_for('home'))


@app.route("/add", methods=["GET", "POST"])
def add_movie():
    form = SearchForm()
    if form.validate_on_submit():
        movie_title = form.movie_name.data
        parameters = {
            "query": movie_title,
            "api_key": MOVIE_API
        }
        response = requests.get(API_URL, params=parameters)
        response.raise_for_status()
        data = response.json()
        movies = [{'movie_title': movie['original_title'], 'year': movie['release_date'], 'id': movie['id'],
                   'poster': movie['poster_path']} for movie
                  in data['results']]
        return render_template("select.html", movies=movies)
    return render_template("add.html", form=form)


@app.route("/find", methods=["GET", "POST"])
def find():
    movie_id = request.args.get('id')
    if movie_id:
        movie_id_api = f'{MOVIE_ID_EP}{movie_id}'
        params = {
            "api_key": MOVIE_API
        }
        response = requests.get(movie_id_api, params=params)
        data = response.json()
        poster = request.args.get('poster')
        new_movie = Movie(
            title=data['original_title'],
            year=data["release_date"].split("-")[0],
            img_url=f"https://image.tmdb.org/t/p/original/{poster}",
            description=data["overview"],
            ranking=0,
            rating=0.0,
            review="type ur review",
        )
        db.session.add(new_movie)
        db.session.commit()
        return redirect(url_for("edit",id=new_movie.id))


if __name__ == '__main__':
    app.run(debug=True)
