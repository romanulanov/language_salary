from statistics import mean
from time import sleep
import requests
from itertools import count
from environs import Env
from terminaltables import AsciiTable


HH_URL = 'https://api.hh.ru/vacancies'
SJ_URL = 'https://api.superjob.ru/2.20/vacancies/'
VACANCIES_PER_PAGE = 20
PROFESSION_ID_SJ = 48
PROFESSION_ID_HH = 96
CITY_ID_SJ = 4
CITY_ID_HH = 4
VACANCIES_NUMBER_LIMIT = 1000


def predict_salary(salary_from, salary_to):
    if (not salary_from and not salary_to) or (not salary_from and not salary_to):
        return None
    elif not salary_from or not salary_from:
        return salary_to * 0.8
    elif not salary_to or not salary_to:
        return salary_from * 1.2
    else:
        return salary_from / 2 + salary_to / 2


def predict_rub_salary_hh(vacancy):
    if vacancy["salary"] and vacancy["salary"]['currency'] == 'RUR':
        return predict_salary(vacancy["salary"]['from'], vacancy["salary"]['to'])


def predict_rub_salary_sj(vacancy):
    if vacancy["currency"] == 'rub':
        return predict_salary(vacancy["payment_from"], vacancy["payment_to"])


def fetch_pages_sj(languages, superjob_key):
    headers = {"X-Api-App-Id": superjob_key}
    vacancies = {}

    for language in languages:
        vacancies[language] = []
        page_number = 1
        page = 0
        while page < page_number:
            params = {
                "town": CITY_ID_SJ,
                "catalogues": PROFESSION_ID_SJ,
                "keyword": language,
                "page": page,
                "count": VACANCIES_PER_PAGE
            }
            
            page_response = requests.get(
                "https://api.superjob.ru/2.0/vacancies/",
                headers=headers,
                params=params,
            )
            page_response.raise_for_status()

            page_payload = page_response.json()
            if page_payload["total"] > VACANCIES_NUMBER_LIMIT:
                page_number = VACANCIES_NUMBER_LIMIT // VACANCIES_PER_PAGE
            elif page_payload["total"] < VACANCIES_PER_PAGE:
                page_number = 1
            else:
                page_number = page_payload["total"] // VACANCIES_PER_PAGE
            page += 1

            page_vacancies = page_payload["objects"]
            vacancies[language].extend(page_vacancies)
            
    return vacancies


def fetch_pages_hh(languages):
    vacancies = {}
    days = 30
    for language in languages:
        vacancies[language] = []
        page_number = 1
        page = 0
        while page < page_number:
            params = {
                "professional_role": PROFESSION_ID_HH,
                "area": CITY_ID_HH,
                "period": days,
                "text": language,
                "search_field": "name",
                "page": page
            }
            
            page_response = requests.get(
                "https://api.hh.ru/vacancies", params=params
            )
            page_response.raise_for_status()

            page_payload = page_response.json()
            page_number = page_payload["pages"]
            page += 1

            page_vacancies = page_payload["items"]
            vacancies[language].extend(page_vacancies)
            
    return vacancies


def calculate_salary(vacancies):
    for language in vacancies:
        if (vacancies[language]["vacancies_processed"]):
            vacancies[language]['average_salary'] = int(vacancies[language]['average_salary'] / vacancies[language]["vacancies_processed"])
    vacancies_with_calculating_salary = vacancies
    return vacancies_with_calculating_salary


def create_table(vacancies, title):
    vacancies_table = [(tuple((language,) + tuple(vacancies[language].values()))) for language in vacancies]
    table = (('Язык программирования', 'Вакансий найдено', 'Вакансий обработано', 'Средняя зарплата'),) + tuple([vacancy for vacancy in vacancies_table])
    table = AsciiTable(table, 'HeadHunter Moscow')
    table.all_columns = 'left'
    return table


def get_vacancies_statistic_hh(vacancies):
    vacancies_statistic = {}
    for language in vacancies:
        salaries = []
        for vacancy in vacancies[language]:
            salary = predict_rub_salary_hh(vacancy)
            if salary:
                salaries.append(salary)
        if not salaries:
            average_salary = 0
        else:
            average_salary = int(mean(salaries))
        vacancies_statistic[language] = {
            "vacancies_found": len(vacancies[language]),
            "vacancies_processed": len(salaries),
            "average_salary": average_salary,
        }
    return vacancies_statistic


def get_vacancies_statistic_sj(vacancies):
    vacancies_statistic = {}
    for language in vacancies:
        salaries = []
        for vacancy in vacancies[language]:
            salary = predict_rub_salary_sj(vacancy)
            if salary:
                salaries.append(salary)
        if not salaries:
            average_salary = 0
        else:
            average_salary = int(mean(salaries))
        vacancies_statistic[language] = {
            "vacancies_found": len(vacancies[language]),
            "vacancies_processed": len(salaries),
            "average_salary": average_salary,
        }
    return vacancies_statistic


def print_table(table, title):
    table_instance = AsciiTable(table, title)
    table_instance.all_columns = 'left'
    print(table_instance.table)


def main():
    env = Env()
    env.read_env()
    sj_token = env("SJ_TOKEN")
    languages = ['JavaScript', 'Java', 'Python', 'Ruby', 'PHP', 'C++', 'C#', 'C', 'Go', 'Shell']
    
    hh_vacancies = fetch_pages_hh(languages)
    hh_vacancies_statistic = get_vacancies_statistic_hh(hh_vacancies)
    sj_vacancies = fetch_pages_sj(languages, sj_token)
    sj_vacancies_statistic = get_vacancies_statistic_sj(sj_vacancies)
    
    hh_table = create_table(hh_vacancies_statistic, 'HeadHunter Moscow')
    print(hh_table.table)
    sj_table = create_table(sj_vacancies_statistic, 'SuperJob Moscow')
    print(sj_table.table)

    



if __name__ == "__main__":
    main()
