# Solana Rug Pull Script

Este script permite configurar varias billeteras de Solana y realizar compras y ventas de tokens utilizando la API de Pump.fun. Además, las billeteras configuradas y los tokens comprados se persisten en archivos para su uso posterior, y todas las operaciones realizadas se registran en un archivo de log.

## Requisitos

1.Python 3.7 o superior
2.Pip (gestor de paquetes de Python)

## Configuración del Entorno Virtual (venv)

Es recomendable crear un entorno virtual (venv) para evitar conflictos entre las dependencias de este proyecto y otras aplicaciones de Python en su sistema.

1. Crear el entorno virtual

```bash
python3 -m venv venv
```

2. Activar el entorno virtual

```bash
source venv/bin/activate
```

3. Instalar las dependencias
   Asegúrate de que el archivo requirements.txt esté en el mismo directorio que el script.

```bash
pip install -r requirements.txt
```

## Ejecutar el Script

Una vez que hayas configurado y activado el entorno virtual, y hayas instalado las dependencias, puedes ejecutar el script:

```bash
make start
```

## Uso del Script

El script te guiará a través de un menú donde podrás:

1. Configurar Billeteras: Configurar una o más billeteras de Solana, asignando un porcentaje de la compra total a cada una.
2. Comprar un Meme Coin: Comprar tokens utilizando las billeteras configuradas.
3. Vender el Token Comprado: Seleccionar y vender un token previamente comprado utilizando las billeteras configuradas.
4. Ver Billeteras Configuradas: Mostrar una lista de las billeteras configuradas, con su porcentaje asignado y el total de tokens comprados.
5. Salir: Salir del script.

## Nota

1. Persistencia: Las billeteras configuradas y los tokens comprados se guardan en archivos de texto (wallets.txt y tokens.txt) para su uso en sesiones futuras.
2. Log de Operaciones: Todas las operaciones realizadas se registran en un archivo de log (wallet_operations.log).

## Desactivar el Entorno Virtual

Una vez que hayas terminado de trabajar, puedes desactivar el entorno virtual con el siguiente comando:

```bash
    deactivate
```

¡Ahora estás listo para usar el script y hacer rug pulls en la red Solana!
