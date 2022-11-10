# Storage

The information is stored in a PostreSQL database. In the python code, the database is managed with the sqlalchemy ORM. That means that the tables in the database can be created from a python class. All of the logic concerning the database is carried out by the DBManager class.

## Schema definition

SRAM samples and sensors are managed by the classes [`Sample`][src.database.Sample] and [`Sensor`][src.database.Sensor] respectively.

## Storing samples and sensor information

```{.py3 title="Example of storing a sample and sensor"}
url = "postgres://username:password@localhost:5432/database"
db = DBManager(url)

sample = Sample(
    uid="DEVICE ID",
    board_id="NUCLEO",
    pic=1,
    address="0x20000000",
    data=",".join([str(d) for d in range(1024)]),
    created_at=datetime.now(),
)
db.insert(sample)

sensor = Sensor(
    uid="DEVICE ID",
    board_id="NUCLEO",
    temperature=27,
    voltage=3300,
)
db.insert(sensor)

db.commit()
```
