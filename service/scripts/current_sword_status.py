from service import models

accounts = models.Account.with_sword_activated()
f = open('repository_status_current_2023_01_25.csv', 'w')
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
