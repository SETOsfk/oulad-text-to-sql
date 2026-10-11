#!/bin/bash
# Mac'te çift tıkla ya da `bash yayinla.command`. Önce https://github.com/new adresinde BOŞ bir "oulad-text-to-sql" reposu aç (README/LICENSE ekleme).
cd "$(dirname "$0")"
git init -q -b main 2>/dev/null || git init -q
git add -A
git status --short | head -50
git commit -q -m "OULAD text-to-SQL: ölçümlü değerlendirme, FastAPI, Docker"
git remote add origin https://github.com/SETOsfk/oulad-text-to-sql.git 2>/dev/null
git pull --rebase origin main
git push -u origin main
