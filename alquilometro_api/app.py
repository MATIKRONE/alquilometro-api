from fastapi import FastAPI

app = FastAPI(title='Alquilómetro API')


@app.get('/')
def read_root() -> dict[str, str]:
    return {'message': 'Bienvenido a Alquilómetro'}
