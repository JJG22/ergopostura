#!/bin/sh
# Solo corre la primera vez que se crea la base. Django crea test_<base> al correr las pruebas.
mysql -uroot -p"$MYSQL_ROOT_PASSWORD" -e "GRANT ALL PRIVILEGES ON \`test\_%\`.* TO '$MYSQL_USER'@'%'; FLUSH PRIVILEGES;"
