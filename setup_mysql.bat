@echo off
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Please run this file as Administrator. Right-click -^> Run as administrator.
    pause
    exit /b 1
)

echo ==========================================
echo  MySQL 8.0.43 - First time setup
echo ==========================================

echo [1/4] Installing MySQL service (if not already installed)...
sc query MySQL80 >nul 2>&1
if %errorlevel% neq 0 (
    "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysqld.exe" --install MySQL80 --defaults-file="C:\ProgramData\MySQL\MySQL Server 8.0\my.ini"
) else (
    echo Already installed.
)

echo [2/4] Starting MySQL service...
net start MySQL80

echo [3/4] Setting root password to 'root'...
"C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" -u root --connect-expired-password -e "ALTER USER 'root'@'localhost' IDENTIFIED BY 'root';" 2>nul
if %errorlevel% neq 0 (
    echo (Password may already be set - skipping)
)

echo [4/4] Creating database bulk_import_db...
"C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" -u root -proot -e "CREATE DATABASE IF NOT EXISTS bulk_import_db CHARACTER SET utf8mb4; FLUSH PRIVILEGES;"

echo.
echo ==========================================
echo  DONE! MySQL is now running.
echo  Root password: root
echo  Database: bulk_import_db
echo ==========================================
echo.
pause