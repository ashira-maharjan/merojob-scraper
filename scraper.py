from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import csv, os, time
from datetime import datetime

# ---------------------------
# File Paths
# ---------------------------
DATA_DIR = "data_file"
os.makedirs(DATA_DIR, exist_ok=True)

TOP_JOBS_CSV = os.path.join(DATA_DIR, "top_jobs.csv")       # raw extraction, new jobs on top
BY_DEADLINE_CSV = os.path.join(DATA_DIR, "by_deadline.csv") # sorted by deadline

FIELDNAMES = ["Job Title", "Company", "Experience", "Level", "Salary", "Apply Before"]

# ---------------------------
# Selenium Setup
# ---------------------------
options = webdriver.ChromeOptions()
options.add_argument("--headless=new")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-gpu")
options.add_argument("--window-size=1920,1080")

driver = webdriver.Chrome(options=options)
driver.get("https://merojob.com/")
wait = WebDriverWait(driver, 30)

# Click "Individual Jobs" tab
try:
    individual_jobs_button = wait.until(
        EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Individual Jobs')]"))
    )
    individual_jobs_button.click()
except:
    print("Could not find 'Individual Jobs' button")
    driver.quit()
    exit()

time.sleep(40)  # wait for jobs to load

# ---------------------------
# Scrape jobs
# ---------------------------
job_elements = wait.until(
    EC.presence_of_all_elements_located(
        (By.CSS_SELECTOR, ".rounded-lg.border.bg-card.text-card-foreground.shadow-sm.hover\\:shadow-xl")
    )
)

scraped_jobs = []

for job in job_elements:
    lines = job.text.split("\n")
    job_title = lines[0] if len(lines) > 0 else "N/A"
    company = lines[1] if len(lines) > 1 else "N/A"
    experience = lines[2] if len(lines) > 2 else "N/A"
    level = "N/A"
    salary = "Not Disclosed"
    apply_before_raw = "N/A"

    for line in lines:
        l = line.lower()
        if "level" in l:
            level = line.split(":")[-1].strip()
        elif "apply before" in l:
            apply_before_raw = line.split(":")[-1].strip()
        elif "rs." in l or "lakh" in l or "negotiable" in l:
            salary = line.strip()

    # Convert Apply Before to YYYY-MM-DD
    try:
        for fmt in ("%d/%m/%Y", "%d %B %Y", "%b %d, %Y"):
            try:
                apply_before = datetime.strptime(apply_before_raw, fmt).strftime("%Y-%m-%d")
                break
            except:
                apply_before = apply_before_raw
    except:
        apply_before = apply_before_raw

    scraped_jobs.append({
        "Job Title": job_title.strip(),
        "Company": company.strip(),
        "Experience": experience.strip(),
        "Level": level,
        "Salary": salary,
        "Apply Before": apply_before
    })

driver.quit()

# ---------------------------
# Load existing CSV
# ---------------------------
def load_csv(path):
    existing_keys = set()
    data = []
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                key = (row["Job Title"], row["Company"])
                existing_keys.add(key)
                data.append(row)
    return existing_keys, data

top_keys, top_old = load_csv(TOP_JOBS_CSV)
deadline_keys, deadline_old = load_csv(BY_DEADLINE_CSV)

# ---------------------------
# Filter new jobs
# ---------------------------
def filter_new(jobs, existing_keys):
    new = []
    for j in jobs:
        key = (j["Job Title"], j["Company"])
        if key not in existing_keys:
            new.append(j)
            existing_keys.add(key)
    return new

top_new = filter_new(scraped_jobs, top_keys)
deadline_new = filter_new(scraped_jobs, deadline_keys)

# ---------------------------
# Combine old + new
# ---------------------------
top_all = top_new + top_old
deadline_all = deadline_new + deadline_old

# Sort by Apply Before date
def parse_date(d):
    try:
        return datetime.strptime(d, "%Y-%m-%d")
    except:
        return datetime.max

deadline_all.sort(key=lambda x: parse_date(x["Apply Before"]))

# ---------------------------
# Save CSVs
# ---------------------------
def save_csv(path, data):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(data)

save_csv(TOP_JOBS_CSV, top_all)
save_csv(BY_DEADLINE_CSV, deadline_all)

print(f"{len(top_new)} new jobs added to '{TOP_JOBS_CSV}'")
print(f"{len(deadline_new)} new jobs added to '{BY_DEADLINE_CSV}' sorted by Apply Before")
