"""
PDF Generation Utilities for Financial Statements
Provides comprehensive PDF generation capabilities for all financial reports
"""

import io
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
import pandas as pd

try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer, PageBreak
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

class FinancialStatementPDFGenerator:
    """Professional PDF generator for financial statements"""
    
    def __init__(self):
        self.styles = None
        self.company_info = {
            'name': 'Company Name',
            'address': 'Company Address',
            'phone': 'Phone Number',
            'email': 'Email Address'
        }
        
    def _setup_styles(self):
        """Setup document styles"""
        if not REPORTLAB_AVAILABLE:
            return None
            
        self.styles = getSampleStyleSheet()
        
        # Custom styles
        self.styles.add(ParagraphStyle(
            'CompanyHeader',
            parent=self.styles['Heading1'],
            fontSize=18,
            spaceAfter=12,
            alignment=TA_CENTER,
            textColor=colors.darkblue
        ))
        
        self.styles.add(ParagraphStyle(
            'StatementTitle',
            parent=self.styles['Heading1'],
            fontSize=16,
            spaceAfter=20,
            alignment=TA_CENTER,
            textColor=colors.black
        ))
        
        self.styles.add(ParagraphStyle(
            'SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=14,
            spaceAfter=12,
            spaceBefore=12,
            textColor=colors.darkblue
        ))
        
        self.styles.add(ParagraphStyle(
            'FilterInfo',
            parent=self.styles['Normal'],
            fontSize=10,
            spaceAfter=12,
            alignment=TA_CENTER,
            textColor=colors.grey
        ))
        
        return self.styles
    
    def _create_header(self, statement_title: str, filters: Dict[str, Any]) -> List:
        """Create document header with company info and statement title"""
        story = []
        
        # Company header
        company_header = Paragraph(self.company_info['name'], self.styles['CompanyHeader'])
        story.append(company_header)
        
        # Statement title
        title = Paragraph(statement_title, self.styles['StatementTitle'])
        story.append(title)
        
        # Filter information
        filter_text = self._format_filter_info(filters)
        filter_para = Paragraph(filter_text, self.styles['FilterInfo'])
        story.append(filter_para)
        story.append(Spacer(1, 20))
        
        return story
    
    def _format_filter_info(self, filters: Dict[str, Any]) -> str:
        """Format filter information for display"""
        parts = []
        
        if 'date_from' in filters and 'date_to' in filters:
            date_from = filters['date_from'].strftime('%B %d, %Y') if hasattr(filters['date_from'], 'strftime') else str(filters['date_from'])
            date_to = filters['date_to'].strftime('%B %d, %Y') if hasattr(filters['date_to'], 'strftime') else str(filters['date_to'])
            
            if filters.get('as_of_date', False):
                parts.append(f"As of {date_to}")
            else:
                parts.append(f"For the period from {date_from} to {date_to}")
        
        if 'companies' in filters and filters['companies']:
            if len(filters['companies']) == 1:
                parts.append(f"Company: {filters['companies'][0]}")
            else:
                parts.append(f"Companies: {', '.join(filters['companies'][:3])}{'...' if len(filters['companies']) > 3 else ''}")
        
        if 'fiscal_years' in filters and filters['fiscal_years']:
            if len(filters['fiscal_years']) == 1:
                parts.append(f"Fiscal Year: {filters['fiscal_years'][0]}")
            else:
                parts.append(f"Fiscal Years: {', '.join(map(str, filters['fiscal_years']))}")
        
        return " | ".join(parts)
    
    def _create_data_table(self, df: pd.DataFrame, column_widths: List[float], 
                          table_style: Optional[List] = None, show_totals: bool = False,
                          total_row_data: Optional[List] = None) -> Table:
        """Create a formatted data table"""
        if df.empty:
            return Table([["No data available"]], colWidths=[sum(column_widths)])
        
        # Prepare table data
        headers = list(df.columns)
        table_data = [headers]
        
        for _, row in df.iterrows():
            formatted_row = []
            for col in headers:
                value = row[col]
                if pd.isna(value):
                    formatted_row.append("")
                elif isinstance(value, (int, float)):
                    if col.lower() in ['amount', 'balance', 'debit', 'credit', 'total', 'net']:
                        formatted_row.append(f"{value:,.2f}")
                    else:
                        formatted_row.append(str(value))
                else:
                    formatted_row.append(str(value))
            table_data.append(formatted_row)
        
        # Add totals row if specified
        if show_totals and total_row_data:
            table_data.append(total_row_data)
        
        # Create table
        table = Table(table_data, colWidths=column_widths)
        
        # Default table style
        default_style = [
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),  # Header
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),  # Header background
        ]
        
        # Right-align numeric columns
        for i, header in enumerate(headers):
            if header.lower() in ['amount', 'balance', 'debit', 'credit', 'total', 'net', 'transactions']:
                default_style.append(('ALIGN', (i, 1), (i, -1), 'RIGHT'))
        
        # Add totals row formatting
        if show_totals and total_row_data:
            default_style.extend([
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),  # Totals row
                ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
            ])
        
        # Apply custom style if provided
        if table_style:
            default_style.extend(table_style)
        
        table.setStyle(TableStyle(default_style))
        return table
    
    def _create_summary_section(self, title: str, metrics: Dict[str, Any]) -> List:
        """Create a summary section with key metrics"""
        story = []
        
        # Section title
        story.append(Paragraph(title, self.styles['SectionHeader']))
        
        # Create metrics table
        metrics_data = []
        for label, value in metrics.items():
            if isinstance(value, (int, float)):
                formatted_value = f"{value:,.2f}"
            else:
                formatted_value = str(value)
            metrics_data.append([label, formatted_value])
        
        if metrics_data:
            metrics_table = Table(metrics_data, colWidths=[3*inch, 2*inch])
            metrics_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 11),
                ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LINEBELOW', (0, 0), (-1, -1), 0.5, colors.grey),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),  # Labels bold
            ]))
            story.append(metrics_table)
        
        story.append(Spacer(1, 12))
        return story
    
    def _create_footer(self) -> List:
        """Create document footer"""
        story = []
        story.append(Spacer(1, 30))
        
        footer_text = f"Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}"
        footer_para = Paragraph(footer_text, self.styles['FilterInfo'])
        story.append(footer_para)
        
        return story
    
    def generate_financial_statement_pdf(self, statement_type: str, df: pd.DataFrame, 
                                       filters: Dict[str, Any], 
                                       summary_data: Optional[Dict[str, Any]] = None,
                                       additional_sections: Optional[List[Dict]] = None) -> Tuple[bytes, str]:
        """Generate PDF for any financial statement"""
        
        if not REPORTLAB_AVAILABLE:
            # Fallback to HTML
            html_content = self._generate_html_fallback(statement_type, df, filters, summary_data)
            return html_content.encode('utf-8'), 'html'
        
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72, 
                              topMargin=72, bottomMargin=72)
        
        # Setup styles
        self._setup_styles()
        
        # Build story
        story = []
        
        # Header
        story.extend(self._create_header(statement_type, filters))
        
        # Main data table
        if not df.empty:
            # Determine column widths based on statement type
            column_widths = self._get_column_widths(statement_type, df)
            
            # Create main table
            main_table = self._create_data_table(df, column_widths)
            story.append(main_table)
            story.append(Spacer(1, 20))
        
        # Summary section
        if summary_data:
            story.extend(self._create_summary_section("Summary", summary_data))
        
        # Additional sections
        if additional_sections:
            for section in additional_sections:
                story.extend(self._create_summary_section(
                    section.get('title', 'Additional Information'),
                    section.get('data', {})
                ))
        
        # Footer
        story.extend(self._create_footer())
        
        # Build PDF
        doc.build(story)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        return pdf_bytes, 'pdf'
    
    def _get_column_widths(self, statement_type: str, df: pd.DataFrame) -> List[float]:
        """Get appropriate column widths for different statement types"""
        num_cols = len(df.columns)
        
        if statement_type.lower() == 'income statement':
            # Account ID, Account Name, Amount, % of Revenue
            return [1.2*inch, 3*inch, 1.5*inch, 1*inch][:num_cols]
        elif statement_type.lower() == 'balance sheet':
            # Account ID, Account Name, Balance
            return [1.2*inch, 3.5*inch, 1.5*inch][:num_cols]
        elif statement_type.lower() == 'trial balance':
            # Account ID, Account Name, Account Type, Debit, Credit, Balance, Transactions
            return [1*inch, 2.5*inch, 1*inch, 1*inch, 1*inch, 1*inch, 0.8*inch][:num_cols]
        elif 'cash flow' in statement_type.lower():
            # Account ID, Account Name, Net Change, Transactions
            return [1.2*inch, 3*inch, 1.5*inch, 1*inch][:num_cols]
        else:
            # Default equal distribution
            available_width = 6.5 * inch
            return [available_width / num_cols] * num_cols
    
    def _generate_html_fallback(self, statement_type: str, df: pd.DataFrame, 
                              filters: Dict[str, Any], 
                              summary_data: Optional[Dict[str, Any]] = None) -> str:
        """Generate HTML fallback when ReportLab is not available"""
        
        filter_text = self._format_filter_info(filters)
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>{statement_type}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ text-align: center; margin-bottom: 30px; }}
                .header h1 {{ margin: 0; font-size: 24px; color: #1f4e79; }}
                .header h2 {{ margin: 10px 0; font-size: 18px; }}
                .filter-info {{ font-size: 12px; color: #666; margin-bottom: 20px; }}
                .data-table {{ width: 100%; border-collapse: collapse; margin-bottom: 30px; }}
                .data-table th, .data-table td {{ padding: 8px; border: 1px solid #ccc; text-align: left; }}
                .data-table th {{ background-color: #f5f5f5; font-weight: bold; }}
                .data-table .numeric {{ text-align: right; }}
                .summary {{ margin-top: 30px; }}
                .summary h3 {{ color: #1f4e79; }}
                .summary-table {{ width: 50%; border-collapse: collapse; }}
                .summary-table td {{ padding: 8px; border-bottom: 1px solid #ccc; }}
                .summary-table .label {{ font-weight: bold; }}
                .footer {{ margin-top: 30px; font-size: 12px; color: #666; text-align: center; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>{self.company_info['name']}</h1>
                <h2>{statement_type}</h2>
                <div class="filter-info">{filter_text}</div>
            </div>
            
            <table class="data-table">
                <thead>
                    <tr>
        """
        
        # Add table headers
        for col in df.columns:
            html_content += f"<th>{col}</th>"
        html_content += """
                    </tr>
                </thead>
                <tbody>
        """
        
        # Add data rows
        for _, row in df.iterrows():
            html_content += "<tr>"
            for col in df.columns:
                value = row[col]
                css_class = "numeric" if col.lower() in ['amount', 'balance', 'debit', 'credit', 'total', 'net'] else ""
                if pd.isna(value):
                    html_content += f'<td class="{css_class}"></td>'
                elif isinstance(value, (int, float)) and css_class:
                    html_content += f'<td class="{css_class}">{value:,.2f}</td>'
                else:
                    html_content += f'<td class="{css_class}">{value}</td>'
            html_content += "</tr>"
        
        html_content += """
                </tbody>
            </table>
        """
        
        # Add summary section
        if summary_data:
            html_content += """
            <div class="summary">
                <h3>Summary</h3>
                <table class="summary-table">
            """
            for label, value in summary_data.items():
                formatted_value = f"{value:,.2f}" if isinstance(value, (int, float)) else str(value)
                html_content += f"""
                    <tr>
                        <td class="label">{label}</td>
                        <td class="numeric">{formatted_value}</td>
                    </tr>
                """
            html_content += """
                </table>
            </div>
            """
        
        html_content += f"""
            <div class="footer">
                Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}
            </div>
        </body>
        </html>
        """
        
        return html_content

# Convenience functions for specific statement types
def generate_income_statement_pdf(df: pd.DataFrame, filters: Dict[str, Any], 
                                summary_data: Dict[str, Any]) -> Tuple[bytes, str]:
    """Generate Income Statement PDF"""
    generator = FinancialStatementPDFGenerator()
    return generator.generate_financial_statement_pdf(
        "Income Statement", df, filters, summary_data
    )

def generate_balance_sheet_pdf(df: pd.DataFrame, filters: Dict[str, Any], 
                             summary_data: Dict[str, Any]) -> Tuple[bytes, str]:
    """Generate Balance Sheet PDF"""
    generator = FinancialStatementPDFGenerator()
    filters['as_of_date'] = True  # Balance sheet is as of a date
    return generator.generate_financial_statement_pdf(
        "Balance Sheet", df, filters, summary_data
    )

def generate_cash_flow_statement_pdf(df: pd.DataFrame, filters: Dict[str, Any], 
                                   summary_data: Dict[str, Any], 
                                   method: str = "Direct Method") -> Tuple[bytes, str]:
    """Generate Statement of Cash Flows PDF"""
    generator = FinancialStatementPDFGenerator()
    title = f"Statement of Cash Flows - {method}"
    return generator.generate_financial_statement_pdf(
        title, df, filters, summary_data
    )

def generate_trial_balance_pdf(df: pd.DataFrame, filters: Dict[str, Any], 
                             summary_data: Dict[str, Any]) -> Tuple[bytes, str]:
    """Generate Trial Balance PDF"""
    generator = FinancialStatementPDFGenerator()
    filters['as_of_date'] = True  # Trial balance is as of a date
    return generator.generate_financial_statement_pdf(
        "Trial Balance Report", df, filters, summary_data
    )