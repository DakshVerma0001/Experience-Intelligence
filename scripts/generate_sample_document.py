"""Generates a realistic sample company experience document for demos/testing.
Mixes newer and older field-label formats across several assignments."""
from docx import Document

doc = Document()
doc.add_heading("AFC India Limited - Company Experience Profile", level=1)

# Assignment 1 - newer format
doc.add_paragraph("Assignment-1")
doc.add_paragraph("Name of Applicant: AFC India Limited")
doc.add_paragraph("Name of Project: National Level PACS Software Vendor")
doc.add_paragraph(
    "Description of services Performed by the Applicant Firm: Design, development and "
    "rollout of an ERP platform for Primary Agricultural Credit Societies (PACS) including "
    "GIS-based branch mapping and data migration."
)
doc.add_paragraph("Name of client and Address: NABARD, Mumbai, Maharashtra")
doc.add_paragraph("Name and telephone no. of client's representative: Mr. Sharma, 022-12345678")
doc.add_paragraph("Estimated capital cost of the Project: Rs. 32.01 Crores")
doc.add_paragraph("Start date: September 2021")
doc.add_paragraph("Finish date: Ongoing")
doc.add_paragraph(
    "Brief description of the Project: Nationwide ERP implementation for PACS digitization "
    "including GIS integration, mobile data collection and dashboards for NABARD."
)

# Assignment 2 - older format
doc.add_paragraph("Assignment-2")
doc.add_paragraph("Assignment / Job name: Co-Working Spaces Portal Development")
doc.add_paragraph("Firm's Name: AFC India Limited")
doc.add_paragraph(
    "Description of Project: Development and maintenance of a portal for co-working spaces "
    "used by government agencies across India, including booking management and API integration."
)
doc.add_paragraph("Approx. value of the Contract: Rs. 1.95 crore")
doc.add_paragraph("Country & Location: India")
doc.add_paragraph("Duration of Assignment / job: 24 months")
doc.add_paragraph("Name of Employer: APCWS")
doc.add_paragraph("Total No. of Staff months: 18")

# Assignment 3 - newer format, completed project
doc.add_paragraph("Assignment-3")
doc.add_paragraph("Name of Applicant: AFC India Limited")
doc.add_paragraph("Name of Project: State Highway Bridge Design Consultancy")
doc.add_paragraph(
    "Description of services Performed by the Applicant Firm: Structural design, survey and "
    "supervision consultancy for bridge construction on the state highway network."
)
doc.add_paragraph("Name of client and Address: National Highways Authority of India (NHAI), New Delhi")
doc.add_paragraph("Estimated capital cost of the Project: Rs. 5.4 Crores")
doc.add_paragraph("Start date: January 2015")
doc.add_paragraph("Finish date: December 2017")
doc.add_paragraph(
    "Brief description of the Project: Completed structural design and construction supervision "
    "consultancy for highway bridge infrastructure."
)

doc.save("../sample-data/company_experience_sample.docx")
print("Sample document generated.")
