from service import models

accounts = models.Account.with_sword_activated()
f = open('repository_status_2023_01_25.csv', 'w')
f.write("id,old_status,new_status\n")
for account in accounts:
    # see if there's a repository status for this account
    rs = models.RepositoryStatus.pull(account.id)

    # if not, that's as good as being deactivated
    if rs is None:
        f.write("{a},,\n".format(a=account.id))
        continue
    if rs.status == 'failing':
        f.write("{a},{b},\n".format(a=account.id, b=rs.status))
    else:
        old_status = rs.status
        rs.deactivate()
        rs.save()
        new_status = rs.status
        f.write("{a},{b},{c}\n".format(a=account.id, b=old_status, c=new_status))

f.close()
