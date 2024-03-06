# 4. How to develop together
- press the fork button in http://mod.lge.com/hub/cheoljoo.lee/weekly_work_report_from_jira
- you can make forked project in your id.
- git clone your forked project
- edit it
- commit and push in your forked project

## 4.1. create Merge Request into original
- click "New Merge Request" in "Merge Request" tab
- source : your forked repository and branch & target : original repository
- press "Compare branches and continue"

## 4.2. How to synchonize between original and forked
- git remote add upstream http://mod.lge.com/hub/cheoljoo.lee/weekly_work_report_from_jira.git
- git remote -v
- git fetch upstream
- git branch -va
- git merge upstream/master
