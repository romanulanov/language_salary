from time import sleep
import requests
from itertools import count
from environs import Env
from terminaltables import AsciiTable


HH_URL = 'https://api.hh.ru/vacancies'
SJ_URL = 'https://api.superjob.ru/2.20/vacancies/'
NUMBER_OF_PAGES = 100
AREA_ID = 1
PROFESSION_ID = 48


def predict_salary(salary_from, salary_to):
    if (not(salary_from) and not(salary_to)) or (not(salary_from) and not(salary_to)):
        return None
    elif not(salary_from) or not(salary_from):
        return salary_to * 0.8
    elif not(salary_to) or not(salary_to):
        return salary_from * 1.2
    else:
        return (salary_from + salary_to) / 2


def predict_rub_salary_hh(vacancy):
    if vacancy["salary"] and vacancy["salary"]['currency'] == 'RUR':
        return predict_salary(vacancy["salary"]['from'], vacancy["salary"]['to'])


def predict_rub_salary_sj(vacancy):
    if vacancy["currency"] == 'rub':
        return predict_salary(vacancy["payment_from"], vacancy["payment_to"])


def fetch_pages_sj(url, language, sj_token):
    for page in count(0):
        try:
            page_response = requests.get(url, 
            params={
            "catalogues": PROFESSION_ID,
            "town": { "id": AREA_ID, "title":"Москва"},
            "page": page,
            "count": NUMBER_OF_PAGES,
            "profession": language
            },
            headers={"X-Api-App-Id": sj_token},
            )
            page_response.raise_for_status()
            page_payload = page_response.json()
            yield from page_payload['objects']
            if not(page_payload["more"]):
                break
        except requests.ReadTimeout:
            continue


def fetch_pages_hh(url, params, language):
    for page in count(0):
        page_response = requests.get(url, params={**params, **{"page": page, 'name': language}})
        page_response.raise_for_status()
        page_payload = page_response.json()
        if page >= page_payload["pages"] - 1:
            break
        yield from page_payload['items']


def create_vacancies():
    languages, vacancies = ['JavaScript', 'Java', 'Python', 'Ruby', 'PHP', 'C++', 'C#', 'C', 'Go', 'Shell'], {}
    for language in languages:
        vacancies[language], vacancies[language]['vacancies_found'], vacancies[language]["vacancies_processed"], vacancies[language]['average_salary'] = {}, 0, 0, 0
    return vacancies


def calculate_salary(vacancies):
    for language in vacancies:
        if (vacancies[language]["vacancies_processed"]):
            vacancies[language]['average_salary'] = int(vacancies[language]['average_salary'] / vacancies[language]["vacancies_processed"])
    vacancies_with_calculating_salary = vacancies
    return vacancies_with_calculating_salary


def create_table(vacancies):
    vacancies_table = [(tuple((language,) + tuple(vacancies[language].values()))) for language in vacancies]
    table = (('Язык программирования', 'Вакансий найдено', 'Вакансий обработано', 'Средняя зарплата'),) + tuple([vacancy for vacancy in vacancies_table])
    return table


def get_vacancies_hh(url, vacancies, params):
    for language in vacancies.keys():
        for vacancy in fetch_pages_hh(url, params, language):
            vacancies_found = vacancies[language]["vacancies_found"] + 1
            vacancies_processed = vacancies[language]["vacancies_processed"]
            average_salary = vacancies[language]['average_salary'] 
            rub_salary_hh = predict_rub_salary_hh(vacancy)
            if rub_salary_hh:
                vacancies_processed = vacancies[language]["vacancies_processed"] + 1
                average_salary = vacancies[language]['average_salary'] + rub_salary_hh
            vacancies[language] = {"vacancies_found": vacancies_found, "vacancies_processed": vacancies_processed, "average_salary": average_salary}
    vacancies_hh = calculate_salary(vacancies)
    return vacancies_hh


def get_vacancies_sj(url, vacancies, token):
    for language in vacancies.keys():
        for vacancy in fetch_pages_sj(url, language, token):
            vacancies_found = vacancies[language]["vacancies_found"] + 1
            vacancies_processed = vacancies[language]["vacancies_processed"]
            average_salary = vacancies[language]['average_salary'] 
            rub_salary_sj = predict_rub_salary_sj(vacancy)
            if rub_salary_sj:
                vacancies_processed = vacancies[language]["vacancies_processed"] + 1
                average_salary = vacancies[language]['average_salary'] + rub_salary_sj
            vacancies[language] = {"vacancies_found": vacancies_found, "vacancies_processed": vacancies_processed, "average_salary": average_salary}
    vacancies_sj = calculate_salary(vacancies)
    return vacancies_sj


def print_table(table, title):
    table_instance = AsciiTable(table, title)
    table_instance.all_columns = 'left'
    print(table_instance.table)


def main():
    env = Env()
    env.read_env()
    sj_token = env("SJ_TOKEN")
    hh_params = {'area': AREA_ID, "per_page": NUMBER_OF_PAGES}
    sj_vacancies, hh_vacancies = create_vacancies(), create_vacancies()
    hh_vacancies = get_vacancies_hh(HH_URL, hh_vacancies, hh_params)
    sj_vacancies = get_vacancies_sj(SJ_URL, sj_vacancies, sj_token)
    hh_table = create_table(hh_vacancies)
    sj_table = create_table(sj_vacancies)
    print_table((hh_table), 'HeadHunter')
    print_table((sj_table), 'SuperJob')


if __name__ == "__main__":
    main()
