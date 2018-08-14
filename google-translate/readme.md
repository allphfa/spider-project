
# google-translate
> use python 3.5 +

```python
from google_translate import translate, ref_words


words = 'python 你好'
ret = translate(words[:4999], to='en', source='zh-CN')
ret = translate(ret[0][:4999], source='en', to='zh-CN')

# 下面这个没啥JB鸟用
# down face this no JB fuck use
# print(ref_words('我在', source='zh', to='en'))
```