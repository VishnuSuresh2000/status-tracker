# Data Directory Protection

This directory contains the SQLite database files for the Status Tracker application.

## Important: Data Protection

⚠️ **WARNING**: Database files in this directory (`*.db`, `*.sqlite`, `*.sqlite3`) are 
**NOT tracked by git** (they are listed in `.gitignore`). This means:

- They won't be committed to version control (good for security)
- They can be accidentally deleted during `git clean` or repository resets
- You must take steps to protect your data

## Protection Measures

### 1. Automatic Backup System

We provide a data protection script that creates backups before risky operations:

```bash
# Create a manual backup
python scripts/protect_data.py backup manual-backup

# List all backups
python scripts/protect_data.py list

# Restore from latest backup
python scripts/protect_data.py restore

# Check data integrity
python scripts/protect_data.py check
```

### 2. Git Hooks (Automatic Protection)

Git hooks have been installed to protect your data:

- **pre-commit**: Warns if database files are accidentally staged
- **pre-clean**: Automatically backs up data before `git clean` operations

### 3. Safe Git Operations

When performing operations that might delete untracked files:

```bash
# Before git clean - backup your data
python scripts/protect_data.py pre-git clean

# Perform the clean
# ... git clean -fd ...

# After clean - restore if needed
python scripts/protect_data.py post-git clean
```

Or use the safer approach:

```bash
# Exclude data directory from clean
git clean -fd --exclude="data/*.db" --exclude="data/*.sqlite" --exclude="data/*.sqlite3"
```

### 4. Docker Volume Protection

When using Docker, the data directory is mounted as a volume:

```yaml
volumes:
  - ./data:/app/data
```

This persists data across container restarts, but be careful when:
- Removing containers with `-v` flag (removes volumes)
- Running `docker-compose down -v`
- Rebuilding images without preserving volumes

## Backup Strategy

### Recommended Backup Workflow

1. **Before major changes**:
   ```bash
   python scripts/protect_data.py backup "before-feature-x"
   ```

2. **Regular automated backups** (add to cron):
   ```bash
   # Daily backup at 2 AM
   0 2 * * * cd /path/to/status-tracker && python scripts/protect_data.py backup daily
   
   # Cleanup old backups weekly (keep last 20)
   0 3 * * 0 cd /path/to/status-tracker && python scripts/protect_data.py cleanup 20
   ```

3. **Before git operations that clean untracked files**:
   ```bash
   python scripts/protect_data.py pre-git clean
   git clean -fd
   python scripts/protect_data.py post-git clean
   ```

## Data Recovery

If your data files are accidentally deleted:

1. **Check for backups**:
   ```bash
   python scripts/protect_data.py list
   ```

2. **Restore latest**:
   ```bash
   python scripts/protect_data.py restore
   ```

3. **If no backups exist**: Check your system backups or version control (if you manually committed data, which is not recommended).

## Configuration

### Environment Variables

You can customize the protection behavior:

```bash
# Backup directory location (default: ./.data_backups)
export DATA_BACKUP_DIR="/path/to/backups"

# Number of backups to keep (default: 10)
export DATA_BACKUP_KEEP_COUNT=20
```

### .gitignore Configuration

The current `.gitignore` settings:

```gitignore
# Database files are ignored (not tracked by git)
data/*.db
data/*.sqlite
data/*.sqlite3

# But the directory itself is kept
!data/.gitkeep
```

**Do not remove these lines** unless you want to track database files in git (not recommended for production data).

## Best Practices

1. ✅ **Always backup before risky operations**
2. ✅ **Use the protection scripts provided**
3. ✅ **Keep backups in a separate location** (copy `.data_backups/` to external storage)
4. ✅ **Test restore procedures** periodically
5. ❌ **Never commit database files to git**
6. ❌ **Never run `git clean -fd` without checking for data files**
7. ❌ **Never use `git checkout -f` or `git reset --hard` carelessly**

## Troubleshooting

### "Database is locked" errors

This usually means another process is using the database. Check:
- Is the application running? (main.py or docker)
- Is the worker running? (worker.py)
- Are multiple processes accessing the database?

### "No backups found" when trying to restore

The protection system only works if you use it:
- Did you create backups before the incident?
- Is the `.data_backups/` directory present?
- Check if backups were accidentally cleaned up

### Data files keep disappearing

If data files are consistently being removed:
1. Check your IDE settings (some IDEs clean untracked files)
2. Check CI/CD pipelines (they might be cleaning the workspace)
3. Check Docker configurations (volumes might not be mounted correctly)
4. Ensure git hooks are installed: `ls -la .git/hooks/`

## Support

For issues or questions about data protection:
1. Check the backup logs in `.data_backups/protection_manifest.json`
2. Review the protection script: `scripts/protect_data.py`
3. Check application logs for errors

Remember: **The best protection is regular backups!**
