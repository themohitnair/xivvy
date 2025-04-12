# xivvy

A Semantic Search Engine for arXiv papers.

**Note:** The search engine explicitly ignores updations to papers which are already added. The routine script just adds new papers (the IDs that have not been added yet).

## To run xivvy locally

First, clone the repository:

```bash
git clone https://github.com/themohitnair/xivvy.git ~/xivvy
```

xivvy uses [uv](https://github.com/astral-sh/uv) for dependency management along with a Python 3.13 interpreter. It is a prerequisite for running the project, among other dependency managers which you may choose to use. The required packages are listed in `requirements.txt`. Notable dependencies include:

* `fastembed`
* `qdrant-client`
* `fastapi`
* `orjson`

To create a virtual environment within the project directory and install all dependencies in `requirements.txt`, you can run the init.sh script:

```bash
#!/usr/bin/bash

set -euo pipefail

echo "Creating virtual environment using uv."
uv venv --python=3.13

echo "Activating virtual environment."
source .venv/bin/activate

echo "Installing dependencies from requirements.txt."
uv pip install -r requirements.txt

echo "Your environment is ready to cook!"
```

The repository root must contain a directory called `kaggle`, within which there must be your `kaggle.json` file containing the following:

```json
{
  "username":<Your Kaggle Username>,
  "key":<Your Kaggle API Key>
}
```

You can obtain this JSON file as it is from this [link](https://www.kaggle.com/settings) under the API section.

Use this command (with or without sudo, depending on your machine) to create a qdrant instance at port 6333:

```bash
sudo docker run -d -p 6333:6333 -v $(pwd)/qdrant_storage:/qdrant/storage qdrant/qdrant
```

This command starts a docker instance for the qdrant database and adds the said directory `qdrant_storage` with the access port 6333.

You can use the following command to find the qdrant docker instance (with or without sudo, depending on your machine):

```bash
sudo docker ps
```

After this, you must add a cronjob to run `./upd.sh` weekly (assuming you want all the arXiv papers to be in scope for your search engine, even the ones appended regularly to it).
