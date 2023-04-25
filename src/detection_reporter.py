import logging
import time
import json
import os
import sys
from jinja2 import Environment, FileSystemLoader
import datetime
from ipaddress import ip_address


class DetectionReporter:

    def __init__(self, output_dir, c2_indicators_total_count, c2_indicators_count, extracted_data, detected_iocs, plugin_c2_hunter):
        self.logger = logging.getLogger(__name__)
        self.base_relative_path = os.path.dirname(os.path.realpath(sys.argv[0]))
        self.template_dir_path = os.path.join(self.base_relative_path, "templates")
        self.report_dir = output_dir
        self.analysis_report_path = os.path.join(self.report_dir, "analysis_report.html")
        self.report_output_path = os.path.join(self.report_dir, "detected_iocs.json")
        self.extracted_data = extracted_data
        self.detected_iocs = detected_iocs
        self.c2_indicators_total_count = c2_indicators_total_count
        self.c2_indicators_count = c2_indicators_count
        self.plugin_c2_hunter = plugin_c2_hunter

    def write_detected_iocs_to_file(self):
        print(f"[{time.strftime('%H:%M:%S')}] [INFO] Preparing detected IOCs for writing to the output file ...")
        self.logger.info(f"Preparing detected IOCs for writing to the output file")
        self.detected_iocs['aggregated_ip_addresses'] = list(self.detected_iocs['aggregated_ip_addresses'])
        self.detected_iocs['aggregated_domain_names'] = list(self.detected_iocs['aggregated_domain_names'])
        self.detected_iocs['aggregated_urls'] = list(self.detected_iocs['aggregated_urls'])

        ip_list = self.detected_iocs['aggregated_ip_addresses']
        public_ips = [ip for ip in ip_list if not ip_address(ip).is_private]
        self.detected_iocs['aggregated_ip_addresses'] = public_ips 

        print(f"[{time.strftime('%H:%M:%S')}] [INFO] Writing detected IOCs to '{self.report_output_path}'")
        self.logger.info(f"Writing detected IOCs '{self.report_output_path}'")

        with open(self.report_output_path, "w") as output:
            output.write(json.dumps(self.detected_iocs, indent=4))

    def create_html_analysis_report(self):
        print(f"[{time.strftime('%H:%M:%S')}] [INFO] Creating an HTML analysis report '{self.analysis_report_path}' ...")
        self.logger.info(f"Creating an HTML analysis report '{self.analysis_report_path}'...")

        # load the Jinja2 template
        env = Environment(loader=FileSystemLoader(self.template_dir_path))
        template = env.get_template("report_template.html")

        current_datetime = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # render the template with the detected_iocs data
        rendered_html = template.render(current_datetime=current_datetime, c2_indicators_total_count=self.c2_indicators_total_count, c2_indicators_count=self.c2_indicators_count, extracted_data=self.extracted_data, detected_iocs=self.detected_iocs, plugin_c2_hunter=self.plugin_c2_hunter)

        # write the report to a file
        with open(self.analysis_report_path, 'w') as f:
            f.write(rendered_html)
