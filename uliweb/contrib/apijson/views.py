#coding=utf-8
from uliweb import expose, functions, models
from uliweb.orm import ModelNotFound
from json import loads
import logging

log = logging.getLogger('apijson')

@expose('/apijson')
class ApiJson(object):
    def __begin__(self):
        try:
            self.request_data = loads(request.data)
        except Exception as e:
            log.error("try to load json but get exception: '%s', request data: %s"%(e,request.data))
            return json({"code":400,"msg":"not json data in the request"})
    
    def get(self):
        self.rdict = {
            "code":200,
            "msg":"success"
        }
        for key in self.request_data:
            if key[-2:]=="[]":
                rsp = self._query_array(key)
            else:
                rsp = self._query_record(key)
            if rsp: return rsp

        return json(self.rdict)

    def _query_record(self,key):
        modelname = key
        try:
            model = getattr(models,modelname)
            model_setting = settings.APIJSON_MODEL.get(modelname,{})
        except ModelNotFound as e:
            log.error("try to find model '%s' but not found: '%s'"%(modelname,e))
            return json({"code":400,"msg":"model '%s' not found"%(modelname)})
        q = model.all()
        public = model_setting.get("public",False)
        filtered = False
        if not public:
            if not request.user:
                return json({"code":401,"msg":"'%s' not accessable for unauthorized request"%(modelname)})
            owner_filtered = False
            if hasattr(model,"owner_condition"):
                q = q.filter(model.owner_condition())
                owner_filtered = True
                filtered = True
            if not owner_filtered:
                user_id_field = model_setting.get("user_id_field")
                if user_id_field:
                    q = q.filter(getattr(model.c,user_id_field)==request.user.id)
                    filtered = True
            if not owner_filtered:
                return json({"code":401,"msg":"'%s' not accessable because not public"%(modelname)})
        params = self.request_data[key]
        if isinstance(params,dict):
            for attrname in params:
                if hasattr(model,attrname):
                    q = q.filter(getattr(model.c,attrname)==params[attrname])
                    filtered = True
                else:
                    return json({"code":400,"msg":"'%s' have no attribute '%s'"%(modelname,attrname)})
        #default filter
        if not filtered and request.user:
            default_filter_by_self = model_setting.get("default_filter_by_self",False)
            if default_filter_by_self:
                user_id_field = model_setting.get("user_id_field")
                if user_id_field:
                    q = q.filter(getattr(model.c,user_id_field)==request.user.id)
                    filtered = True
        o = q.one()
        if o:
            o = o.to_dict()
            secret_fields = model_setting.get("secret_fields")
            if secret_fields:
                for k in secret_fields:
                    del o[k]
        self.rdict[key] = o

    def _query_array(self,key):
        params = self.request_data[key]
        count = None
        modelname = None
        model_param = None
        model_column_set = None
        for n in params:
            if n[0]=="@":
                if n=="@count":
                    try:
                        count = int(params[n])
                    except ValueError as e:
                        log.error("bad param in '%s': '%s'"%(n,params))
                        return json({"code":400,"msg":"@count should be an int, now '%s'"%(params[n])})
                    if count<=0:
                        return json({"code":400,"msg":"count should >0, now is '%s' "%(count)})
            else:
                # TODO: support join in the future, now only support 1 model
                modelname = n
        
        if not modelname:
            return json({"code":400,"msg":"no model found in array query"})

        model_param = params[n]
        model_column = model_param.get("@column")
        if model_column:
            model_column_set = set(model_column.split(","))
        try:
            model = getattr(models,modelname)
        except ModelNotFound as e:
            log.error("try to find model '%s' but not found: '%s'"%(modelname,e))
            return json({"code":400,"msg":"model '%s' not found"%(modelname)})
        model_setting = settings.APIJSON_MODEL.get(modelname,{})
        secret_fields = model_setting["secret_fields"]
        public = model_setting.get("public",False)

        q = model.all()
        if count:
            q = q.limit(count)
        if not public:
            if not request.user:
                return json({"code":401,"msg":"'%s' not accessable for unauthorized request"%(modelname)})
            

        def _get_info(i):
            d = i.to_dict()
            if secret_fields:
                for k in secret_fields:
                    del d[k]
            if model_column_set:
                keys = list(d.keys())
                for k in keys:
                    if k not in model_column_set:
                        del d[k]
            return d
        l = [_get_info(i) for i in q]
        self.rdict[key] = l
