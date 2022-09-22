import json

from flask import Flask, jsonify, request
from flask_restful import Resource, Api
import zxing
from werkzeug.utils import secure_filename
from flask_cors import CORS
import sqlite3
import requests
import urllib.request

app = Flask(__name__)
api = Api(app)
CORS(app, resource={'*': '*'})
conn = sqlite3.connect("database.db", isolation_level=None, check_same_thread=False)


class DetectBarcode(Resource):
    def post(self):
        f = request.files['image']
        f.save('./barcode_images/' + secure_filename(f.filename))
        f.close()
        reader = zxing.BarCodeReader()
        barcode = reader.decode('./barcode_images/' + secure_filename(f.filename))
        return jsonify({
            "barcode": barcode.parsed
        })


class SearchObject(Resource):
    def get(self):
        barcode = request.args.get('barcode')

        # 0단계: 바코드 검사
        if len(str(barcode)) != 13:
            return jsonify({
                "message": "유효하지 않은 바코드입니다."
            })

        # 1단계: 상품 검색
        r = requests.get(f'https://www.retaildb.or.kr/service/product_info/search/{barcode}')
        r = r.json()
        if r['code'] == '2000':
            print(r)
            return jsonify({
                "message": "유효하지 않은 바코드입니다."
            })
        object_name = r['baseItems'][0]['value']
        object_image = r['images'][0]

        # 2단계: 가격 분석
        cur2 = conn.cursor()
        history_price = cur2.execute(f"SELECT 일,이,삼,사,오,육,칠,팔 FROM price WHERE 상품명 LIKE '%{object_name}%'")
        history_price = cur2.fetchall()
        cur1 = conn.cursor()
        now_price = cur1.execute(f"SELECT 판매가격 FROM goods WHERE 상품명 LIKE '%{object_name}%'")
        now_price = cur1.fetchone()

        client_id = "4NQy_M3UAe3Q7SQiIm_5"
        client_secret = "sEnjJ8wAe6"
        encText = urllib.parse.quote(object_name)
        url = "https://openapi.naver.com/v1/search/news?query=" + encText  # JSON 결과
        _request = urllib.request.Request(url)
        _request.add_header("X-Naver-Client-Id", client_id)
        _request.add_header("X-Naver-Client-Secret", client_secret)
        response = urllib.request.urlopen(_request)
        rescode = response.getcode()
        if (rescode == 200):
            response_body = response.read()
            # print(response_body.decode('utf-8'))
        else:
            print("Error Code:" + rescode)
        # return
        print(history_price)
        _history_price = {
            '2020년 4분기': '데이터 없음',
            '2021년 1분기': '데이터 없음',
            '2021년 2분기': '데이터 없음',
            '2021년 3분기': '데이터 없음',
            '2021년 4분기': '데이터 없음',
            '2022년 1분기': '데이터 없음',
            '2022년 2분기': '데이터 없음',
            '2022년 3분기': '데이터 없음',
        }
        for i in range(len(history_price[0])):
            if history_price[0][i] != None:
                a=list(_history_price.keys())
                _history_price[a[i]] = history_price[0][i] + '원'
        return jsonify({
            "now_price": now_price,
            "history_price": _history_price,
            "image": object_image,
            "classification": r['clsTotalNm'],
            "maker": r['companies'],
            "news": json.loads(response_body.decode('utf-8'))
        })


api.add_resource(DetectBarcode, '/barcode/img')
api.add_resource(SearchObject, '/search')

if __name__ == '__main__':
    app.run(port='2000', debug=True)
