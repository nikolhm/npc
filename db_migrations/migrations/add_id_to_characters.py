from commands import create_oracle_connection

def up () :
    connection = create_oracle_connection()
    cursor = connection.cursor()
    cursor.execute("ALTER TABLE characters ADD id NUMBER(10)")
    cursor.execute("CREATE SEQUENCE characters_seq START WITH 1 INCREMENT BY 1")
    cursor.execute("UPDATE characters SET id = characters_seq.nextval")
    cursor.execute("ALTER TABLE characters MODIFY id NOT NULL")
    cursor.execute("ALTER TABLE characters ADD CONSTRAINT characters_pk PRIMARY KEY (id)")
    cursor.execute("ALTER TABLE characters MODIFY id DEFAULT characters_seq.nextval")
    connection.commit()
    cursor.close()

def down () :
    connection = create_oracle_connection()
    cursor = connection.cursor()
    cursor.execute("ALTER TABLE characters DROP COLUMN id")
    cursor.execute("DROP SEQUENCE characters_seq")
    connection.commit()
    cursor.close()