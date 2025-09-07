"""
Sample test data generator for the file converter application.
"""

import csv
import json
from pathlib import Path


def create_sample_csv():
    """Create a sample CSV file for testing."""
    sample_data = [
        ['Name', 'Age', 'City', 'Department', 'Salary'],
        ['John Doe', '28', 'New York', 'Engineering', '75000'],
        ['Jane Smith', '32', 'Los Angeles', 'Marketing', '68000'],
        ['Bob Johnson', '25', 'Chicago', 'Sales', '55000'],
        ['Alice Brown', '29', 'Houston', 'Engineering', '72000'],
        ['Charlie Wilson', '35', 'Phoenix', 'Management', '85000'],
        ['Diana Davis', '27', 'Philadelphia', 'Design', '62000'],
        ['Eve Martinez', '31', 'San Antonio', 'Marketing', '70000'],
        ['Frank Miller', '26', 'San Diego', 'Engineering', '73000'],
        ['Grace Taylor', '30', 'Dallas', 'Sales', '58000'],
        ['Henry Anderson', '33', 'San Jose', 'Management', '88000']
    ]
    
    with open('sample_employees.csv', 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerows(sample_data)
    
    print("Created sample_employees.csv")


def create_sample_xml():
    """Create a sample XML file for testing."""
    xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
<library>
    <books>
        <book id="1">
            <title>The Great Gatsby</title>
            <author>F. Scott Fitzgerald</author>
            <year>1925</year>
            <genre>Classic Literature</genre>
            <price currency="USD">12.99</price>
            <in_stock>true</in_stock>
        </book>
        <book id="2">
            <title>To Kill a Mockingbird</title>
            <author>Harper Lee</author>
            <year>1960</year>
            <genre>Classic Literature</genre>
            <price currency="USD">13.99</price>
            <in_stock>true</in_stock>
        </book>
        <book id="3">
            <title>1984</title>
            <author>George Orwell</author>
            <year>1949</year>
            <genre>Dystopian Fiction</genre>
            <price currency="USD">14.99</price>
            <in_stock>false</in_stock>
        </book>
        <book id="4">
            <title>Pride and Prejudice</title>
            <author>Jane Austen</author>
            <year>1813</year>
            <genre>Romance</genre>
            <price currency="USD">11.99</price>
            <in_stock>true</in_stock>
        </book>
        <book id="5">
            <title>The Catcher in the Rye</title>
            <author>J.D. Salinger</author>
            <year>1951</year>
            <genre>Coming-of-age</genre>
            <price currency="USD">13.50</price>
            <in_stock>true</in_stock>
        </book>
    </books>
    <metadata>
        <total_books>5</total_books>
        <last_updated>2024-01-15</last_updated>
        <library_name>Central Public Library</library_name>
    </metadata>
</library>'''
    
    with open('sample_library.xml', 'w', encoding='utf-8') as xmlfile:
        xmlfile.write(xml_content)
    
    print("Created sample_library.xml")


def create_sample_complex_csv():
    """Create a more complex CSV with special characters and various data types."""
    complex_data = [
        ['Product_ID', 'Product_Name', 'Description', 'Price', 'Category', 'Launch_Date', 'Is_Available'],
        ['PROD001', 'Smartphone Pro', 'High-end smartphone with 128GB storage', '899.99', 'Electronics', '2023-01-15', 'True'],
        ['PROD002', 'Café Latte Maker', 'Premium coffee machine for home use', '299.50', 'Appliances', '2023-02-20', 'True'],
        ['PROD003', 'Gaming Laptop', 'High-performance laptop for gaming enthusiasts', '1299.00', 'Electronics', '2023-03-10', 'False'],
        ['PROD004', 'Organic Green Tea', 'Premium organic green tea, 50 tea bags', '24.99', 'Food & Beverage', '2023-01-05', 'True'],
        ['PROD005', 'Bluetooth Headphones', 'Wireless noise-canceling headphones', '199.99', 'Electronics', '2023-04-01', 'True'],
        ['PROD006', 'Yoga Mat Premium', 'Eco-friendly yoga mat with carrying bag', '89.99', 'Sports & Fitness', '2023-02-14', 'True'],
        ['PROD007', 'Smart Watch', 'Fitness tracking smartwatch with GPS', '349.00', 'Electronics', '2023-03-25', 'False'],
        ['PROD008', 'Artisan Chocolate Box', 'Handcrafted chocolates, assorted flavors', '45.50', 'Food & Beverage', '2023-01-30', 'True']
    ]
    
    with open('sample_products.csv', 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerows(complex_data)
    
    print("Created sample_products.csv")


if __name__ == "__main__":
    # Create sample files in the current directory
    create_sample_csv()
    create_sample_xml()
    create_sample_complex_csv()
    
    print("\nSample files created successfully!")
    print("You can use these files to test the converter:")
    print("- sample_employees.csv")
    print("- sample_library.xml") 
    print("- sample_products.csv")
