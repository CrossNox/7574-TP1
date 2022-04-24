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

# Ejecución con Docker
Desde la carpeta `docker`, ejecutar:

```bash
docker-compose up --build
```

El anterior comando crea un contenedor que ejecuta el servidor, dos contenedores que ejecutan un cliente que envía métricas y un contenedor que monitorea las notificaciones.

## Makefile
Para probar distintos escenarios, se provee un archivo `Makefile` con los siguientes comandos:

TODO
