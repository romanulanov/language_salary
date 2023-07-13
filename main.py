import requests
from itertools import count
from environs import Env
from terminaltables import AsciiTable


HH_API = 'https://api.hh.ru/vacancies'
SJ_API = 'https://api.superjob.ru/2.20/vacancies/'


def predict_salary(salary_from, salary_to):
    if (salary_from == None and salary_to == None) or (salary_from == 0 and salary_to == 0):
        return None
    elif salary_from == None or salary_from == 0:
        return salary_to * 0.8
    elif salary_to == None or salary_to == 0:
        return salary_from * 1.2
    else:
        return (salary_from + salary_to) / 2


def predict_rub_salary_hh(vacancy):
    if vacancy["salary"] != None and vacancy["salary"]['currency'] == 'RUR':
        return predict_salary(vacancy["salary"]['from'], vacancy["salary"]['to'])
    else: 
        return None


def predict_rub_salary_sj(vacancy):
    if vacancy["currency"] == 'rub':
        return predict_salary(vacancy["payment_from"], vacancy["payment_to"])
    else:
        return None


def fetch_records_sj(url, language, sj_token):
    page_response = requests.get(url, params={"keyword":language, "catalogues":48, "town":"Москва", "period":0, "page":0, "count":100}, headers= {"X-Api-App-Id":sj_token })
    page_response.raise_for_status()
    page_payload = page_response.json()
    page = 0
    yield from page_payload['objects']
    while page_payload["more"] == 'True':
        page+=1
        page_payload = requests.get(url, params={"keyword":language, "catalogues":48, "town":"Москва", "period":0, "page":page, "count":100}, headers= {"X-Api-App-Id":sj_token })
        page_payload = page_response.json()
        yield from page_payload['objects']


def fetch_records_hh(url, params, language):
    for page in count(0):  
        page_response = requests.get(url, params={**params,**{"page": page, 'text': language}})
        page_response.raise_for_status()
        page_payload = page_response.json()
        yield from page_payload['items']
        if page >= page_payload["pages"] - 1:
            break


def create_vacancies():
    languages, vacancies = ['JavaScript', 'Java', 'Python', 'Ruby', 'PHP', 'C++', 'C#', 'C', 'Go', 'Shell'], {}
    for language in languages:
        vacancies[language],vacancies[language]['vacancies_found'], vacancies[language]["vacancies_processed"], vacancies[language]['average_salary'] = {}, 0, 0, 0
    return vacancies


def calculate_salary(vacancies):
    for language in vacancies:
        if vacancies[language]["vacancies_processed"] !=0:
            vacancies[language]['average_salary'] = int(vacancies[language]['average_salary'] / vacancies[language]["vacancies_processed"])
    return vacancies


def create_table(vacancies):
    vacancies_table = [(tuple((language,) + tuple(vacancies[language].values()))) for language in vacancies]
    table = (('Язык программирования', 'Вакансий найдено', 'Вакансий обработано', 'Средняя зарплата'),) + tuple([vacancy for vacancy in vacancies_table])
    return table

def get_vacancies_hh(url, vacancies, params):
    for language in vacancies.keys():
        for vacancy in fetch_records_hh(url, params, language):
            if language.lower() in vacancy['name'].lower():
                vacancies[language]["vacancies_found"] += 1
                if predict_rub_salary_hh(vacancy):
                    vacancies[language]["vacancies_processed"] += 1
                    vacancies[language]['average_salary'] += predict_rub_salary_hh(vacancy)          
    vacancies = create_table(calculate_salary(vacancies))
    return vacancies


def get_vacancies_sj(url, vacancies, token):
    for language in vacancies.keys():
        for vacancy in fetch_records_sj(url, language, token):
            if language.lower() in vacancy["profession"].lower():
                vacancies[language]["vacancies_found"] += 1
                if predict_rub_salary_sj(vacancy):
                    vacancies[language]["vacancies_processed"] += 1
                    vacancies[language]['average_salary'] += predict_rub_salary_sj(vacancy)
    vacancies = create_table(calculate_salary(vacancies))
    return vacancies



def print_table(table, title):
    table_instance = AsciiTable(table, title)
    table_instance.all_columns = 'left'
    print(table_instance.table)


def main():    
    env = Env()
    env.read_env()    
    sj_token = env("SJ_TOKEN")
    hh_params = {'area':"1", "per_page": 100}
    sj_vacancies, hh_vacancies = create_vacancies(), create_vacancies()
    hh_vacancies = get_vacancies_hh(HH_API, hh_vacancies, hh_params)
    sj_vacancies = get_vacancies_sj(SJ_API, sj_vacancies, sj_token)
    print_table((hh_vacancies), 'HeadHunter')
    print_table((sj_vacancies), 'SuperJob')
    
    
if __name__ == "__main__":
    main()
