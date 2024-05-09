Clone the repo
You should somewhere have legacy MySQL database for this
Change env vars in Dockerfile for db creds
build image: docker build -t my-fin-image.
run dockerfile: $ docker run -dp 5000:5000 --network host --name my-fin-container my-fin-image
