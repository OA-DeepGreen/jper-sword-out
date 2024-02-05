from service import models
from datetime import date

accounts = models.Account.with_sword_activated()
today = date.today().strftime("%Y-%m-%d")
f = open(f"repository_status_{today}.csv", 'a')
f.write("id,old_status,new_status\n")
for account in accounts:
    # Get repository status for this account
    rs = models.RepositoryStatus.pull(account.id)
    if rs is None:
        # if no repository status, that's as good as being deactivated
        f.write("{a},,\n".format(a=account.id))
        continue
    if rs.status == 'failing':
        f.write("{a},{b},\n".format(a=account.id, b=rs.status))
    else:
        # status could be problem or succeeding
        old_status = rs.status
        rs.deactivate()
        rs.save()
        new_status = rs.status
        f.write("{a},{b},{c}\n".format(a=account.id, b=old_status, c=new_status))

f.close()

