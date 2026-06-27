import pymysql

pymysql.version_info = (2, 2, 1, "final", 0)  # ⚠️ QUAN TRỌNG (fake version)
pymysql.install_as_MySQLdb()
