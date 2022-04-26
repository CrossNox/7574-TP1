# metrics_server
TP1 para 7574 - Distribuidos I.

# Arquitectura
Referirse a `informe/informe.pdf`.

# Instalación
El proyecto fue empaquetado con [poetry](https://python-poetry.org/) para manejar dependencias cómodamente. Puede seguir la [guía de instalación](https://python-poetry.org/docs/#installation) para instalar la herramienta.

Teniendo `poetry` instalado, el siguiente comando creará un nuevo entorno para poder ejecutar el proyecto:

```bash
poetry install --no-dev
```

# Configuración
En el root del proyecto se provee un archivo `sample_settings.ini` con los posibles valores de configuración. Sin embargo, el archivo esperado se llama `settings.ini`. Por motivos obvios de seguridad, este archivo es ignorado en el sistema de versionado con `.gitignore`.

Puede copiar el archivo de prueba provisto, renombrarlo y modificar los valores según necesidad.

Cada posible configuración se puede sobreescribir con variables de entorno con la nomenclatura`<Seccion>_<Clave>`. Por ejemplo `SERVER_HOST`.

# Ejecución
## Server
Revisar el mensaje de ayuda del servidor:

```bash
poetry run metrics_server --help
```

## Client
Revisar el mensaje de ayuda del cliente:

```bash
poetry run metrics_client --help
```

Para ver el mensaje de ayuda de cada uno de los subcomandos:

```bash
poetry run metrics_client <command> --help
```

# Ejecución con Docker
Desde la carpeta `docker`, ejecutar:

```bash
docker-compose up --build
```

El anterior comando crea un contenedor que ejecuta el servidor, dos contenedores que ejecutan un cliente que envía métricas y un contenedor que monitorea las notificaciones.

## Makefile
Para probar distintos escenarios, se provee un archivo `Makefile` con comandos para ejecutar los siguientes escenarios durante la demo:

Para cada escenario:
```bash
make docker-compose-scenario<nro>
make docker-compose-scenario<nro>-down
```

### Escenario 1
En este escenario:
- Se envía una métrica `foo` durante 120 segundos, 2 veces por segundo
- Se envía una métrica `bar` durante 120 segundos, 2 veces por segundo
- Se monitorea la métrica `foo` por un promedio mayor a 10 en un período de 1 segundo
	- Debería suceder alrededor del segundo 10, con los valores 10 y 11
- Se monitorea la métrica `bar` por un valor máximo mayor a 10 en un período de 1 segundo
	- Debería suceder alrededor del segundo 11, con el valor 11

### Escenario 2
En este escenario:
- Se envía una métrica `foo` durante 20 segundos, 5 veces por segundo
- Se hace una query para la métrica `foo` sin intervalo agregando cada 0 segundos, por máximo
	- Debería devolver una lista con los valores de 1 a 100

### Escenario 3
En este escenario:
- Se envía una métrica `foo` durante 20 segundos, 5 veces por segundo
- Se hace una query para la métrica `bar` sin intervalo agregando cada 0 segundos, por máximo
	- Debería registrar que no existe la métrica `bar`

### Escenario 4
En este escenario:
- Se envía una métrica `foo` durante 60 segundos, con crecimiento exponencial de cantidad de métricas por segundo, arrancando en 1 y finalizando en 250
- Se envía una métrica `bar` durante 60 segundos, con crecimiento exponencial de cantidad de métricas por segundo, arrancando en 1 y finalizando en 250
- Se monitora la métrica `foo` agregando por count mayor a 100 en un período de 1 segundo
