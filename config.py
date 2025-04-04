class Config:
    SQLALCHEMY_DATABASE_URI = "mssql+pyodbc://maythawee:Maymys@393833@documentupdown.database.windows.net/document?driver=ODBC+Driver+17+for+SQL+Server"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.urandom(24)  # ใช้เพื่อการป้องกัน CSRF
    AZURE_STORAGE_CONNECTION_STRING = "DefaultEndpointsProtocol=https;AccountName=dicument;AccountKey=kNsfaJcueg9DHYtFlkEn8BL38zZdQjzz6ApjrfmzjUjSMtli/UhhHdVdNeyECgHtONp8ckgvGCXc+AStMR22xw==;EndpointSuffix=core.windows.net"