import argparse
import sys
import os
import platform
import yaml
import logging
import time

from src.analyst_profile import AnalystProfile
from src.packet_parser import PacketParser
from src.enrichment_engine import EnrichmentEngine
from src.detection_engine import DetectionEngine


def banner():
    print(r"""
   ____ ____  ____       _            _   _
  / ___|___ \|  _ \  ___| |_ ___  ___| |_(_)_   _____
 | |     __) | | | |/ _ \ __/ _ \/ __| __| \ \ / / _ \
 | |___ / __/| |_| |  __/ ||  __/ (__| |_| |\ V /  __/
  \____|_____|____/ \___|\__\___|\___|\__|_| \_/ \___|

    """)


def is_platfrom_supported():
    machine_platfrom = platform.system().lower()
    if not machine_platfrom.startswith('linux'):
        print("\n[{time.strftime('%H:%M:%S')}] [CRITICAL] Unsupported platform.")
        logging.critical(f"Unsupported platform")
        print("\nExiting program ...\n")
        sys.exit(1)


def is_valid_file(filename, filetype):
    if not os.path.exists(filename):
        print(
            f"[{time.strftime('%H:%M:%S')}] [ERROR] Provided file '{filename}' does not exist.")
        logging.error(f"Provided file '{filename}' does not exist")
        print("\nExiting program ...\n")
        sys.exit(1)
    else:
        if filetype == "pcap":  # check if the filetype is .pcap or .cap
            if not (filename.endswith(".pcap") or filename.endswith(".cap") or filename.endswith(".pcapng")):
                print(
                    f"[{time.strftime('%H:%M:%S')}] [ERROR] Provided file '{filename}' is not a pcap/cap file.")
                logging.error(
                    f"Provided file '{filename}' is not a pcap/cap file")
                print("\nExiting program ...\n")
                sys.exit(1)
        if filetype == "yml":
            if not filename.endswith(".yml") or filename.endswith(".yaml"):
                print(
                    f"[{time.strftime('%H:%M:%S')}] [ERROR] Provided file '{filename}' is not a yaml file.")
                logging.error(f"Provided file '{filename}' is not a yaml file")
                print("\nExiting program ...\n")
                sys.exit(1)
    return True


def check_required_structure(output_dir):
    base_relative_path = f"{os.path.dirname(os.path.realpath(sys.argv[0]))}"
    report_dir = f"{base_relative_path}/reports"
    iocs_dir = f"{base_relative_path}/iocs"
    tor_iocs_dir = f"{base_relative_path}/iocs/tor"
    cypto_iocs_dir = f"{base_relative_path}/iocs/crypto_domains"
    config_dir = f"{base_relative_path}/config"

    if not output_dir == "reports":
        report_dir = output_dir

    if not os.path.isdir(report_dir):
        print(
            f"[{time.strftime('%H:%M:%S')}] [INFO] Creating '{report_dir}' for storing analysis reports ...")
        logging.info(f"Creating '{report_dir}' for storing analysis reports")
        os.mkdir(report_dir)

    missing_update_script = False
    missing_config_files = False
    if not os.path.isdir(config_dir):
        print(f"[{time.strftime('%H:%M:%S')}] [INFO] Creating '{config_dir}' for storing config files ...")
        logging.info(f"Creating '{config_dir}' for config files")
        os.mkdir(config_dir)
        missing_config_files = True

    if not os.path.isdir(iocs_dir):
        print(f"[{time.strftime('%H:%M:%S')}] [INFO] Creating '{iocs_dir}' for storing IOCs ...")
        logging.info(f"Creating '{iocs_dir}' for storing IOCs")
        os.mkdir(iocs_dir)
        missing_update_script = True
    
    if not os.path.isdir(tor_iocs_dir):
        print(f"[{time.strftime('%H:%M:%S')}] [INFO] Creating '{tor_iocs_dir}' for storing Tor node lists ...")
        logging.info(f"Creating '{tor_iocs_dir}' for storing Tor node lists")
        os.mkdir(tor_iocs_dir)
        missing_update_script = True

    if not os.path.isdir(cypto_iocs_dir):
        print(f"[{time.strftime('%H:%M:%S')}] [INFO] Creating '{cypto_iocs_dir}' for crypto / cryptojacking based sites list ...")
        logging.info(f"Creating '{cypto_iocs_dir}' for crypto / cryptojacking based sites list")
        os.mkdir(cypto_iocs_dir)
        missing_update_script = True

    if missing_update_script:
        print(f"[{time.strftime('%H:%M:%S')}] [ERROR] Download the missing update scripts from 'https://github.com/martinkubecka/C2Detective/tree/main/iocs'")
        logging.error(f"Download the missing update scripts from 'https://github.com/martinkubecka/C2Detective/tree/main/iocs'")
        print("\nExiting program ...\n")
        sys.exit(1)

    if missing_config_files:
        print(f"[{time.strftime('%H:%M:%S')}] [ERROR] Create the missing config files or download them from 'https://github.com/martinkubecka/C2Detective/tree/main/iocs'")
        logging.error(f"Create the missing config files or download them from 'https://github.com/martinkubecka/C2Detective/tree/main/iocs'")
        print("\nExiting program ...\n")
        sys.exit(1)
        


def load_config(filename):
    with open(filename, "r") as ymlfile:
        config = yaml.safe_load(ymlfile)
    return config


def arg_formatter():
    # source : https://stackoverflow.com/questions/52605094/python-argparse-increase-space-between-parameter-and-description
    def formatter(prog): return argparse.HelpFormatter(
        prog, max_help_position=52)
    return formatter


def parse_arguments():
    parser = argparse.ArgumentParser(formatter_class=arg_formatter(), prog='c2detective',
                                     description='Application for detecting command and control (C2) '
                                                 'communication through network traffic analysis.')

    parser.add_argument(
        '-q', '--quiet', help="do not print banner", action='store_true')
    # parser.add_argument('-i', help='input file (.cap OR .pcap)', metavar='FILE', required=True,
    #                     type=lambda file: is_valid_file(file))
    # parser.add_argument('-i', '--input', metavar='FILE',
    #                     help='input file (.cap OR .pcap)', required=True)

    parser.add_argument('input', metavar='FILENAME',
                        help='input file (.cap OR .pcap)')
    # parser.add_argument('-n', '--name', metavar="NAME",
    #                     help='analysis keyword (e.g. Trickbot, Mirai, Zeus, ...)')
    parser.add_argument('-c', '--config', metavar='FILE', default="config/config.yml",
                        help="config file (default: 'config/config.yml')")  # add option to load arguments config file
    parser.add_argument('-s', '--statistics', action='store_true',
                        help='print packet capture statistics')
    parser.add_argument('-r', '--report-iocs', action='store_true',
                        help='write extracted IOCs to JSON file')
    parser.add_argument('-e', '--enrich', action='store_true',  # TODO: should not be action='store_true'
                        help="enable data enrichment")
    # parser.add_argument('-a', '--action', metavar="ACTION",
    #                     help='action to execute [sniffer/...]')
    parser.add_argument('-o', '--output', metavar='PATH', default="reports",
                        help="output directory file path for report files (default: 'reports/')")
    
    parser.add_argument('-utn', '--update-tor-nodes', action='store_true',
                        help='update tor nodes list')   
    parser.add_argument('-ucd', '--update-crypto-domains', action='store_true',
                        help='update crypto / cryptojacking based sites list')   
    

    return parser.parse_args(args=None if sys.argv[1:] else ['--help'])


def init_logger():
    logging_path = f"{os.path.dirname(os.path.realpath(sys.argv[0]))}/logs"
    if not os.path.isdir(logging_path):
        os.mkdir(logging_path)
    logging.basicConfig(format='%(created)f; %(asctime)s; %(levelname)s; %(name)s; %(message)s',
                        filename=f"{logging_path}/c2detective.log",
                        level=logging.DEBUG)  # consider json/yml format for log file
    logger = logging.getLogger('__name__')


def main():
    os.system("clear")
    # print("\033[H\033[J", end="")   # clean screen

    init_logger()
    is_platfrom_supported()

    args = parse_arguments()

    if not args.quiet:
        banner()

    terminal_size = os.get_terminal_size()

    print('-' * terminal_size.columns)
    print(f"[{time.strftime('%H:%M:%S')}] [INFO] Verifying required directory structure ...")
    logging.info("Verifying required directory structure")
    output_dir = args.output
    check_required_structure(output_dir)

    print('-' * terminal_size.columns)
    # TODO: add check if IOCs are present in the project
    if args.update_tor_nodes:
        from iocs.tor.update_tor_nodes import TorNodes
        tor_nodes = TorNodes()
        tor_nodes.update_tor_nodes()
    else:
        file_path = f"{os.path.dirname(os.path.realpath(sys.argv[0]))}/iocs/tor/tor_nodes.json"
        if os.path.exists(file_path):
            modified_time = os.path.getmtime(file_path)
            current_time = time.time()
            time_diff = current_time - modified_time

            # Tor node list was not updated in the last 30 minutes
            if not time_diff < 1800:
                print(f"[{time.strftime('%H:%M:%S')}] [INFO] It is recommended to update the Tor node list every 30 minutes (use '-utn' next time)")
                logging.info(f"It is recommended to update the Tor node list every 30 minutes (use '-utn' next time)")
        else:
            print(f"[{time.strftime('%H:%M:%S')}] [ERROR] Required file '/iocs/tor/tor_nodes.json' does not exist (use '-utn' next time)")
            logging.error(f"Required file '{file_path}' does not exist (use '-utn' next time)")
            print("\nExiting program ...\n")
            sys.exit(1)

    if args.update_crypto_domains:
        from iocs.crypto_domains.update_crypto_domains import CryptoDomains
        crypto_domains = CryptoDomains()
        crypto_domains.update_crypto_domains()
    else:
        file_path = f"{os.path.dirname(os.path.realpath(sys.argv[0]))}/iocs/crypto_domains/crypto_domains.json"
        if os.path.exists(file_path):
            modified_time = os.path.getmtime(file_path)
            current_time = time.time()
            time_diff = current_time - modified_time

            # crypto domains list was not updated in the last 24 hours
            if not time_diff < 24 * 60 * 60: 
                print(f"[{time.strftime('%H:%M:%S')}] [INFO] It is recommended to update the crypto / cryptojacking based sites list every 24 hours (use '-ucd' next time)")
                logging.info(f"It is recommended to update the crypto / cryptojacking based sites list every 24 hours (use '-ucd' next time)")
        else:
            print(f"[{time.strftime('%H:%M:%S')}] [ERROR] Required file '/iocs/crypto_domains/crypto_domains.json' does not exist (use '-ucd' next time)")
            logging.error(f"Required file '{file_path}' does not exist (use '-ucd' next time)")
            print("\nExiting program ...\n")
            sys.exit(1)

    # use analysis name for output/report naming etc.
    # if not args.name is None:
    #     analysis_name = args.name

    print('-' * terminal_size.columns)
    if not args.config is None:
        if is_valid_file(args.config, "yml"):
            print(
                f"[{time.strftime('%H:%M:%S')}] [INFO] Loading config '{args.config}' ...")
            logging.info(f"Loading config '{args.config}'")
            config = load_config(args.config)
            analyst_profile = AnalystProfile(config)
            # analyst_profile.print_config()

    if not args.enrich is None:
        print(
            f"[{time.strftime('%H:%M:%S')}] [INFO] Configurating data enrichment engine ...")
        logging.info("Configurating data enrichment engine")
        enrichment_enchine = EnrichmentEngine(analyst_profile, output_dir)
        # ----------------- TESTING -----------------
        # enrichment_enchine.enrich_data("139.180.203.104")   # Cobalt Strike
        # enrichment_enchine.enrich_data("147.175.111.17")  # STU - open ports and a lot of vulns
        # enrichment_enchine.enrich_data("23.105.223.5")  # lot of abuse
        # enrichment_enchine.enrich_data("027.ru")
        # enrichment_enchine.enrich_data("5577")    # ASN for bgp ranking
        # enrichment_enchine.enrich_data("66.54.96.58") #  Mozi.m
        # exit()

    print('-' * terminal_size.columns)
    input_file = args.input
    if is_valid_file(input_file, "pcap"):
        print(f"[{time.strftime('%H:%M:%S')}] [INFO] Loading '{input_file}' file ...")
        logging.info(f"Loading '{input_file}' file")
        report_iocs = args.report_iocs
        statistics = args.statistics
        packet_parser = PacketParser(
            input_file, output_dir, report_iocs, statistics)
   
    print('-' * terminal_size.columns)
    print(f"[{time.strftime('%H:%M:%S')}] [INFO] Configurating detection engine ...")
    logging.info("Configurating detection engine")
    detection_engine = DetectionEngine(packet_parser, enrichment_enchine)
    detection_engine.detect_connections_with_excessive_frequency()
    detection_engine.detect_long_connection()
    detection_engine.detect_big_HTML_response_size()
    detection_engine.detect_dga() # TODO: works but disable printing warnings/error to console
    detection_engine.detect_known_malicious_HTTP_headers()
    detection_engine.detect_tor_traffic()
    detection_engine.detect_outgoing_traffic_to_tor()
    detection_engine.detect_crypto_domains() 
    # using set() to remove duplicates and check for values count
    no_enabled_services = len(list(set(list(config.get('enrichment_services').values())))) == 1
    # do not use enrichment services when all services are set to 'False'
    if not no_enabled_services:
        detection_engine.threat_feeds()
        # print(f"[{time.strftime('%H:%M:%S')}] [INFO] No enrichment service is enabled ...")
        # logging.info("No enrichment service is enabled")
    detection_engine.evaluate_detection()

    # TODO
    # print('-' * terminal_size.columns)
    # action = args.action

    print('-' * terminal_size.columns)
    print(f"\n[{time.strftime('%H:%M:%S')}] [INFO] All done. Exiting program ...\n")
    logging.info("All done. Exiting program")


if __name__ == '__main__':
    main()

# NOTE: data enrichment caching system/database
# may be useful when running c2detective periodicly in the same environment  