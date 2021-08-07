# JPER SWORD OUT Core Models

This application provides only a small number of models in order to track and persist the state of repositories
and the deposits against them.

* [Repository Status](https://github.com/JiscPER/jper-sword-out/blob/develop/docs/system/RepositoryStatus.md) - the current known state of the repository, recording whether it is failing to accept deposits or if
there are any current active problems with depositing.  It allows the workflow to determine whether to make a deposit
at that time or not.

* [Deposit Record](https://github.com/JiscPER/jper-sword-out/blob/develop/docs/system/DepositRecord.md) - for each deposit, a record of when the deposit happened and the results of each of the components of
the deposit (metadata deposit, binary deposit, and completion).  Note that this model is only persisted when the configuration
says to do so.

This application also shares its index with the JPER core, and accesses the Account model from that system directly.
