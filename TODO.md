# TODO

- [X] Enforce weather constraint and add weather to ui
- [X] Show scenario where bc low wind it is better to do schedule task than breakdown
        // change to 21st of jan to illustrate that downtime is cheap b/c of low wint that it is better to postspone breakdown fix
- [X] Show breakdown time as line in ganttchart
- [X] Make night shifts more expensive
- [X] make toogle to switch btwn optimized and original

backend
- [X] Tasks prior to the breakdown needs to be locked in time
- [X] We need spill over, which is tasks have to happen after the grace period
- [X] Backlog of tasks that has been overdue (maybe show them in yellow on day 1 of the plan)
        shown as tasks passed the spill-over date
- [X] Make delayed Repairs more expensive than delayed routine maintencane
- [X] Show Objective Function with initial plan
- [X] Enable optimization without breakdown
- [ ] Make Robustness KPI (avg Hours btwn tasks or amount of overtime, some metric on how robust is the plan to unforseen disruptions) Robustness to changes in weather

frontend
- [ ] make breakdown on which windmill configuarable in frontend
- [X] collapsed view on windmill level that folds out to show underlying tasks
- [X] make different shapes for repair: corrective and preventive: preventive
- [ ] Make difference in KPIs more visiable in big in green etc


Revenue per hour for the days with downtime for breakdown2.json when penalty per day is set at 30.000. 62,45*24+(24-10)*39,33+24*400+24*314,61+5*400