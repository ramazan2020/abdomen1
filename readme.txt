python -m app.scripts.bootstrap_admin --email admin@example.com --password Admin1234! --name "Yönetici"
python -m app.scripts.bootstrap_admin --email doktor@example.com --password doktor1234! --name "Doktor"

python webapp/scripts/bulk_import.py `
  --source train `
  --email "admin@example.com" `
  --password "Admin1234!" `
  --dataset "Abdomen"
  
  
  
  # Ardından test/yarışma verisi (359 case)  
python webapp/scripts/bulk_import.py `
  --source comp `
  --email "admin@example.com" `
  --password "Admin1234!" `
  --dataset "Abdomen"
