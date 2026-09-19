from flask import jsonify


def success(data=None, message='ok', code=200, status=200):
    return jsonify({'code': code, 'message': message, 'data': data}), status


def list_success(items, total, page, page_size, message='ok'):
    payload = {
        'items': items,
        'total': total,
        'page': page,
        'pageSize': page_size,
    }
    return success(data=payload, message=message)


def error(message, code, status=None, data=None):
    http_status = status if status is not None else code
    return jsonify({'code': code, 'message': message, 'data': data}), http_status

