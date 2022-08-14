# Things to Demo

- `./intro`

## Without explicit typing

- Present `finddups.py` and show its general functionality
- `./finddups.py -l -m20000 ~/tmp`
- `./finddups.py -l ~/tmp | wc` (907 1541 81790)
- `./finddups.py -l ~/tmp | bat` (search "colors")
- `mypy finddups.py`
- `pytype finddups.py` (Google)
- `pyright finddups.py` (Microsoft)
    - Misreport (?) on 33 of `.strip()`
    - Good catch on 177 of possible `None`

## Adding type annotations

- `compare finddups.py finddups2.py`
- Show the equivalence of the modification
    - `./finddups2.py -l ~/tmp | wc`
- `mypy finddups2.py`
- `pytype finddups2.py`
- `pyright finddups2.py`
- Correct the type complaints
    - `compare finddups2.py finddups2a.py`
    - `mypy finddups2a.py`
    - `pytype finddups2a.py`
    - `pyright finddups2a.py`

## Runtime typing

- `compare finddups2.py finddups3.py`
- Show the equivalence of the modification
    - `./finddups3.py -l ~/tmp | wc`
- `mypy finddups3.py`
- `pytype finddups3.py`
- `pyright finddups3.py`
- Introduce a typing error in `finddups4.py`
    - `compare finddups3.py finddups4.py`
    - `mypy finddups3.py`
    - `pytype finddups3.py`
    - `pyright finddups3.py`
    - Not hit at runtime `./finddups4.py -l ~/tmp | wc`

## Third-party use of runtime typing

- Show `runtime_checks.py`
- Run `runtime_checks.py`
- Typing error is clearer and more remediable than traceback
- Mild type coercion in models;

    >>> from typing import AnyStr
    >>> from pydantic import BaseModel
    >>> class Finfo(BaseModel):
    ...     path: AnyStr
    ...     size: int
    ...     inode: int
    >>> finfo = Finfo(path='/path/to/here', size=3.1415, inode=12345678)
    >>> finfo
    Finfo(path=b'/path/to/here', size=3, inode=12345678)
    >>> finfo.json()
    '{"path": "/path/to/here", "size": 3, "inode": 12345678}'

## Fast-API: Pydantic as a microservice

- Launch server: `uvicorn main:app --reload`
- `cp servers/hello.py main.py`
- `curl -s http://localhost:8000 | jq`
- `cp servers/hello-path.py main.py`
- `curl -s http://localhost:8000/item/1234 | jq`
- `curl -s http://localhost:8000/item/not-an-int | jq`
- `cp servers/post-model.py main.py`
- POST some data:

    curl -s -X POST http://localhost:8000/finfo \
    -H 'Content-Type: application/json' \
    -d '{"path":"/some/path","size":100,"inode":99999}' | jq

- POST some not-quite-right data to coerce:

    curl -s -X POST http://localhost:8000/finfo \
    -H 'Content-Type: application/json' \
    -d '{"path":"/some/path","size":3.14,"inode":99999}' | jq

- POST some very-wrong data:

    curl -s -X POST http://localhost:8000/finfo \
    -H 'Content-Type: application/json' \
    -d '{"path":"/some/path","size":null,"inode":99999}' | jq

