from service import models
from datetime import date

accounts = models.Account.with_sword_activated()
today = date.today().strftime("%Y-%m-%d")
f = open(f"repository_sword_status_current_{today}.csv", 'w')
f.write("id,old_status\n")
for account in accounts:
    # see if there's a repository status for this account
    rs = models.RepositoryStatus.pull(account.id)
    if rs is None:
        status = ''
    else:
        status = rs.status
    f.write("{a},{b}\n".format(a=account.id, b=status))

f.close()

