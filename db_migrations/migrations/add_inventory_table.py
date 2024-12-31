from commands import create_oracle_connection

def up():
    connection = create_oracle_connection()
    cursor = connection.cursor()
    # Inventory table structure: 
    # id NUMBER(10) NOT NULL primary key,
    # character_id NUMBER(10) NOT NULL REFERENCES characters(id),
    # name VARCHAR2(100) NOT NULL,
    # quantity NUMBER(10) NOT NULL,
    # info VARCHAR2(255),
    # price NUMBER(10) NOT NULL,
    # discount NUMBER(10), -> discount percentage
    # discount_threshold NUMBER(10), -> value players can roll to get a discount
    cursor.execute("CREATE TABLE inventory (id NUMBER(10) NOT NULL, character_id NUMBER(10) NOT NULL, name VARCHAR2(100) NOT NULL, quantity NUMBER(10) NOT NULL, info VARCHAR2(255), price NUMBER(10) NOT NULL, discount NUMBER(10), discount_threshold NUMBER(10))")
    cursor.execute("CREATE SEQUENCE inventory_seq START WITH 1 INCREMENT BY 1")
    cursor.execute("ALTER TABLE inventory ADD CONSTRAINT inventory_pk PRIMARY KEY (id)")
    cursor.execute("ALTER TABLE inventory MODIFY id DEFAULT inventory_seq.nextval")
    cursor.execute("ALTER TABLE inventory ADD CONSTRAINT inventory_fk FOREIGN KEY (character_id) REFERENCES characters(id)")
    connection.commit()
    cursor.close()

def down():
    connection = create_oracle_connection()
    cursor = connection.cursor()
    cursor.execute("DROP TABLE inventory")
    cursor.execute("DROP SEQUENCE inventory_seq")
    connection.commit()
    cursor.close()