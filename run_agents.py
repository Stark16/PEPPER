from agents.agent1 import JobScreener

screener = JobScreener()
filtered_jobs = screener.run("data/mock_jobs.json")
print(filtered_jobs)
