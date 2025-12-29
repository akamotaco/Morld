using System;
using Godot;

namespace Mysix
{
    using mType = Int32; //System.Int64;

    // http://blog.wouldbetheologian.com/2011/11/fast-approximate-sqrt-method-in-c.html

    public class Approximate
    {
        public static mValue Sqrtf(mValue v)
        {
            return new mValue(Mathf.Sqrt(v.ToFloat()));
        }
        public static mValue Sinf(mValue v)
        {
            return new mValue(Mathf.Sin(v.ToFloat()));
        }
        public static mValue Cosf(mValue v)
        {
            return new mValue(Mathf.Cos(v.ToFloat()));
        }
        // public static float Sqrt(float z)
        // {
        //     if (z == 0) return 0;
        //     FloatIntUnion u;
        //     u.tmp = 0;
        //     u.f = z;
        //     u.tmp -= 1 << 23; /* Subtract 2^m. */
        //     u.tmp >>= 1; /* Divide by 2. */
        //     u.tmp += 1 << 29; /* Add ((b + 1) / 2) * 2^m. */
        //     return u.f;
        // }

        // [System.Runtime.InteropServices.StructLayout(System.Runtime.InteropServices.LayoutKind.Explicit)]
        // private struct FloatIntUnion
        // {
        //     [System.Runtime.InteropServices.FieldOffset(0)]
        //     public float f;

        //     [System.Runtime.InteropServices.FieldOffset(0)]
        //     public int tmp;
        // }

        // public static float Sqrt2(float z) // famous inverse square root method in Quake 3
        // {
        //     if (z == 0) return 0;
        //     FloatIntUnion u;
        //     u.tmp = 0;
        //     float xhalf = 0.5f * z;
        //     u.f = z;
        //     u.tmp = 0x5f375a86 - (u.tmp >> 1);
        //     u.f = u.f * (1.5f - xhalf * u.f * u.f);
        //     return u.f * z;
        // }

        private static mValue _half = mValue.New(0.5f);
        private static mValue _oneNhalf = mValue.New(1.5f);
        // public static Value Sqrt2(Value z) // famous inverse square root method in Quake 3
        // {
        //     if (z == Value.Zero) return Value.Zero;
        //     FloatIntUnion u;
        //     u.tmp = 0;
        //     Value xhalf = z.multiply(_half);
        //     u.f = z.ToFloat();
        //     u.tmp = 0x5f375a86 - (u.tmp >> 1);
        //     Value uf = Value.New(u.f);
        //     xhalf._multiply(uf);
        //     xhalf._multiply(uf);
        //     xhalf._negative();
        //     xhalf._add(_oneNhalf);
        //     uf._multiply(xhalf);
        //     uf._multiply(z);
        //     return uf;
        // }
    }

    public class mValue : IDisposable
    {
        private bool disposed = false;
        public void Dispose()
        {
            Dispose(disposing: true);
            GC.SuppressFinalize(this);
        }
        protected virtual void Dispose(bool disposing)
        {
            if(!this.disposed)
            {
                if(disposing)
                {
                    // TODO: dispose managed state (managed objects).
                }
                {
                    // TODO: free unmanaged resources (unmanaged objects) and override a finalizer below.
                    // TODO: set large fields to null.
                }
                disposed = true;
            }
        }

        ///
        
        ~mValue() {
            this.Dispose(disposing: false);
        }

        protected readonly bool IsReadOnly;
        private void CheckReadOnly()
        {
            if(IsReadOnly) // occur error
                throw new ArgumentException("read only class");
        }

        private const int _bitsSize = sizeof(mType)*8;

        private const int _resolutionBit = 11;
        private const float _resolutionUpper = (float)(0x1<<_resolutionBit);
        private const int _roundBit = (int)(0x1<<(_resolutionBit-1));
        private const int _bitmask = (int)(-1<<(_resolutionBit));

        private mType _value;

        override public string ToString()
        {
            return this.ToFloat().ToString();
        }
        
        public static readonly mValue Zero = mValue.New(0, isReadOnly:true);
        public static readonly mValue One = mValue.New(1, isReadOnly:true);
        public static readonly mValue Two = mValue.New(2, isReadOnly:true);
        public static readonly mValue Half = mValue.New(0.5f, isReadOnly:true);
        public static readonly mValue Eps = mValue.New((float)(1.0/Math.Pow(2,(double)_resolutionBit)), isReadOnly:true);
        public static readonly mValue MaxValue = mValue.New(0x1<<(_bitsSize-_resolutionBit-1)-1, isReadOnly:true);
        public static readonly mValue MinValue = mValue.New(0x1<<(_bitsSize-_resolutionBit)-1, isReadOnly:true);

        #region pooling
        public static mValue New(int v=0, bool isReadOnly=false)
        {
            return new mValue(v, isReadOnly:isReadOnly);
        }
        public static mValue New(float v, bool isReadOnly=false)
        {
            return new mValue(v, isReadOnly:isReadOnly);
        }
        public static mValue New(mValue v, bool isReadOnly=false)
        {
            return new mValue(v, isReadOnly:isReadOnly);
        }
        private static mValue NewRaw(int v)
        {
            var vv = new mValue();
            vv._value = v;
            return vv;
        }
#endregion
        
        public mValue(mValue value, bool isReadOnly=false)
        {
            IsReadOnly = isReadOnly;
            _value = value.Raw;
        }
        public mValue(int value=0, bool isReadOnly=false)
        {
            IsReadOnly = isReadOnly;
            _value = (mType)value<<_resolutionBit;
        }
        public mValue(float value, bool isReadOnly=false)
        {
            IsReadOnly = isReadOnly;
            _value = (mType)(value*_resolutionUpper);//+0.5f);
        }

        public float ToFloat()
        {
            return _value/_resolutionUpper;
        }

        public int ToInt()
        {
            return (mType)_value >> _resolutionBit;
        }

        public mType Raw {get{return _value;}}

        public mValue _add(mValue m)
        {
            CheckReadOnly();
            _value += m.Raw;
            return this;
        }
        public mValue _subtract(mValue m)
        {
            CheckReadOnly();
            _value -= m.Raw;
            return this;
        }

        public mValue add(mValue value)
        {
            return this.clone()._add(value);
        }

        internal mValue multiply(mValue value)
        {
            return this.clone()._multiply(value);
        }

        public mValue _multiply(mValue value)
        {
            CheckReadOnly();
            _value = (_value*value.Raw+_roundBit)>>_resolutionBit;
            return this;
        }

        internal mValue subtract(mValue value)
        {
            return this.clone()._subtract(value);
        }

        internal mValue divide(mValue value)
        {
            return this.clone()._divide(value);
        }

        public mValue _divide(mValue value)
        {
            CheckReadOnly();
            _value =  (_value<<_resolutionBit+_roundBit)/value.Raw;
            return this;
        }

        public mValue _copy(mValue value)
        {
            CheckReadOnly();
            _value = value.Raw;
            return this;
        }
        public mValue clone()
        {
            return mValue.New(this);
        }

        internal mValue _square()
        {
            CheckReadOnly();
            _value = (_value*_value+_roundBit) >> _resolutionBit;
            return this;
        }

        internal mValue _round()
        {
            CheckReadOnly();
            _value = (_value + _roundBit) >> _resolutionBit << _resolutionBit;
            return this;
        }

        internal mValue round()
        {
            return this.clone()._round();
        }

        public mValue square()
        {
            return this.clone()._square();
        }

        internal int CompareTo(mValue mValue)
        {
            return _value.CompareTo(mValue.Raw);
        }

        public override bool Equals(object obj)
        {
            //
            // See the full list of guidelines at
            //   http://go.microsoft.com/fwlink/?LinkID=85237
            // and also the guidance for operator== at
            //   http://go.microsoft.com/fwlink/?LinkId=85238
            //
            
            if (obj is null || GetType() != obj.GetType())
            {
                return false;
            }

            mValue value  = (mValue)obj;
            return this.Raw.Equals(value.Raw);
        }
        
        // override object.GetHashCode
        public override int GetHashCode()
        {
            return this.Raw.GetHashCode();
            // return base.GetHashCode();
        }

        internal void _set(float v)
        {
            CheckReadOnly();
            _value = (mType)(v*_resolutionUpper);//+0.5f);
        }

        internal void _set(int v)
        {
            CheckReadOnly();
            _value = (mType)(v<<_resolutionBit);
        }

        internal void _set(mValue v)
        {
            CheckReadOnly();
            _value = v.Raw;
        }

        internal void _zero()
        {
            CheckReadOnly();
            _value = 0;
        }

        internal void _negative()
        {
            CheckReadOnly();
            _value = -_value;
        }

        public static bool operator == (mValue v1, mValue v2)
        {
            if(v1 is null && v2 is null) return true;
            if(v1 is null || v2 is null) return false;
            return v1.CompareTo(v2) == 0;
        }
        public static bool operator != (mValue v1, mValue v2)
        {
            if(v1 is null && v2 is null) return false;
            if(v1 is null || v2 is null) return true;

            return v1.CompareTo(v2) != 0;
        }
        public static bool operator < (mValue v1, mValue v2)
        {
            return v1.CompareTo(v2) < 0;
        }
        public static bool operator > (mValue v1, mValue v2)
        {
            return v1.CompareTo(v2) > 0;
        }
        public static bool operator <= (mValue v1, mValue v2)
        {
            return v1.CompareTo(v2) <= 0;
        }
        public static bool operator >= (mValue v1, mValue v2)
        {
            return v1.CompareTo(v2) >= 0;
        }

        public static mValue operator * (mValue v1, mValue v2)
        {
            return v1.multiply(v2);
        }
        public static mValue operator / (mValue v1, mValue v2)
        {
            return v1.divide(v2);
        }
        public static mValue operator + (mValue v1, mValue v2)
        {
            return v1.add(v2);
        }
        public static mValue operator - (mValue v1, mValue v2)
        {
            return v1.subtract(v2);
        }

        public static mValue operator * (int v1, mValue v2)
        {
            return new mValue(v1)*v2;
        }

        public static mValue operator - (mValue v)
        {
            var res = v.clone();
            res._negative();
            return res;
        }

        internal void _abs()
        {
            CheckReadOnly();
            _value = Math.Abs(_value);
        }

        internal void _sign()
        {
            CheckReadOnly();
            if(_value == 0)
                _value = 0;
            else
                _value = _value > 0 ? 1<<_resolutionBit : -1<<_resolutionBit;
        }

        internal mValue sign()
        {
            var value = this.clone();
            value._sign();
            return value;
        }

        internal bool isZero()
        {
            return _value == 0;
        }

        internal mValue abs()
        {
            var v = this.clone();
            v._abs();
            return v;
        }

        internal static mValue Max(mValue srcSize, mValue dstSize)
        {
            return srcSize > dstSize ? srcSize : dstSize;
        }

        internal static mValue Min(mValue srcSize, mValue dstSize)
        {
            return srcSize < dstSize ? srcSize : dstSize;
        }

        internal static mValue Parse(int value)
        {
            return new mValue(value);
        }
        internal static mValue Parse(float value)
        {
            return new mValue(value);
        }

        internal static mValue angleFromVector2D(mValue x, mValue y)
        {
            return atan2(x, y);
        }

        internal static mValue atan2(mValue x, mValue y)
        {
            return mValue.Parse(Mathf.Atan2(x.ToFloat(), y.ToFloat()));
        }

        internal mValue floor()
        {
            return mValue.NewRaw(this._value & _bitmask);
        }
    }

    public class mVector4 : mVector3
    {
        public mVector4(mVector3 vec) : base(vec)
        {
            _xyzw[3]._set(vec.w);
        }
        public mVector4(int x=0,int y=0,int z=0,int w=0) : base(x,y,z)
        {
            _xyzw[3]._set(w);
        }

        public mVector4(float x,float y,float z,float w) : base(x,y,z)
        {
            _xyzw[3]._set(w);
        }
        public mVector3 ToVector3()
        {
            return this as mVector3;
        }
    }

#region vector2
    public class mVector2
    {
        protected readonly bool IsReadOnly;
        private void CheckReadOnly()
        {
            if(IsReadOnly) // occur error
                throw new ArgumentException("read only class");
        }

        protected mValue[] _xy = null;
        public mValue x{get{return _xy[0];}}
        public mValue y{get{return _xy[1];}}

        public static readonly mVector2 Zero = new mVector2(0,0, isReadOnly:true);
        public static readonly mVector2 One = new mVector2(1,1, isReadOnly:true);
        public static readonly mVector2 Half = new mVector2(0.5f,0.5f, isReadOnly:true);

        public mValue[] _raw(){return _xy;}

        public mVector2 clone()
        {
            return new mVector2(_xy[0],_xy[1]);
        }

        public mVector2(mValue x,mValue y, bool isReadOnly=false)
        {
            IsReadOnly = isReadOnly;
            // if(_xy == null) _xy = new mValue[2]{mValue.New(),mValue.New()};
            _xy = new mValue[2]{mValue.New(),mValue.New()};
            _xy[0]._set(x);
            _xy[1]._set(y);
        }

        public mVector2(mVector2 xy, bool isReadOnly=false)
        {
            IsReadOnly = isReadOnly;
            // if(_xy == null) _xy = new mValue[4]{mValue.New(),mValue.New(),mValue.New(),mValue.New()};
            _xy = new mValue[4]{mValue.New(),mValue.New(),mValue.New(),mValue.New()};
            _xy[0]._set(xy._xy[0]);
            _xy[1]._set(xy._xy[1]);
        }

        public mVector2(int x=0,int y=0, bool isReadOnly=false)
        {
            IsReadOnly = isReadOnly;
            // if(_xy == null) _xy = new mValue[4]{mValue.New(),mValue.New(),mValue.New(),mValue.New()};
            _xy = new mValue[4]{mValue.New(),mValue.New(),mValue.New(),mValue.New()};
            _xy[0]._set(x);
            _xy[1]._set(y);
        }
        public mVector2(float x,float y, bool isReadOnly=false)
        {
            IsReadOnly = isReadOnly;
            // if(_xy == null) _xy = new mValue[4]{mValue.New(),mValue.New(),mValue.New(),mValue.New()};
            _xy = new mValue[4]{mValue.New(),mValue.New(),mValue.New(),mValue.New()};
            _xy[0]._set(x);
            _xy[1]._set(y);
        }

        public mVector2 _add(mVector2 vec)
        {
            CheckReadOnly();
            _xy[0]._add(vec.x);
            _xy[1]._add(vec.y);
            return this;
        }
        public mVector2 _subtract(mVector2 vec)
        {
            CheckReadOnly();
            _xy[0]._subtract(vec.x);
            _xy[1]._subtract(vec.y);
            return this;
        }

        internal mVector2 add(mVector2 vec)
        {
            return this.clone()._add(vec);
        }

        internal mVector2 subtract(mVector2 vec)
        {
            return this.clone()._subtract(vec);
        }

        public mValue magnitude() // ???
        {
            return _xy[0].square()._add(_xy[1].square());
        }

        internal mValue distance() // ???
        {
            return Approximate.Sqrtf(this.magnitude());
        }

        internal static mVector2 vectorFromAngle(mValue direction)
        {
            var vec = new mVector2();
            vec.y._set(Approximate.Cosf(direction));
            vec.x._set(Approximate.Sinf(direction));
            
            return vec;
        }

        public static mVector2 operator + (mVector2 vec1, mVector2 vec2)
        {
            return vec1.add(vec2);
        }
        public static mVector2 operator - (mVector2 vec1, mVector2 vec2)
        {
            return vec1.subtract(vec2);
        }
    }
#endregion

#region Vector3
    public class mVector3 : IDisposable
    {
        private bool disposed = false;
        public void Dispose()
        {
            Dispose(disposing: true);
            GC.SuppressFinalize(this);
        }
        protected virtual void Dispose(bool disposing)
        {
            if(!this.disposed)
            {
                if(disposing)
                {
                    // TODO: dispose managed state (managed objects).
                    _xyzw = null;
                }
                {
                    // TODO: free unmanaged resources (unmanaged objects) and override a finalizer below.
                    // TODO: set large fields to null.
                }
                disposed = true;
            }
        }

        ///
        
        ~mVector3() {
            this.Dispose(false);
        }

        protected readonly bool IsReadOnly;
        private void CheckReadOnly()
        {
            if(IsReadOnly) // occur error
                throw new ArgumentException("read only class");
        }

        protected mValue[] _xyzw = null;
        public mValue x{get{return _xyzw[0];}}
        public mValue y{get{return _xyzw[1];}}
        public mValue z{get{return _xyzw[2];}}
        public mValue w{get{return _xyzw[3];}}

        public static readonly mVector3 Zero = new mVector3(0,0,0, isReadOnly:true);

        internal mValue sum()
        {
            var value = new mValue();
            value._add(x);
            value._add(y);
            value._add(z);
            return value;
        }

        public static readonly mVector3 One = new mVector3(1,1,1, isReadOnly:true);

        public mValue[] _raw() {
            CheckReadOnly();
            return _xyzw;
        }

        public mVector3(mValue x,mValue y,mValue z, bool isReadOnly=false)
        {
            this.IsReadOnly = isReadOnly;
            // if(_xyzw == null) _xyzw = new mValue[4]{mValue.New(),mValue.New(),mValue.New(),mValue.New()};
            _xyzw = new mValue[4]{mValue.New(),mValue.New(),mValue.New(),mValue.New()};
            _xyzw[0]._set(x);
            _xyzw[1]._set(y);
            _xyzw[2]._set(z);
            // _xyzw[3]._set(0);
        }

        public mVector3(mVector3 xyz, bool isReadOnly=false)
        {
            this.IsReadOnly = isReadOnly;

            // if(_xyzw == null) _xyzw = new mValue[4]{mValue.New(),mValue.New(),mValue.New(),mValue.New()};
            _xyzw = new mValue[4]{mValue.New(),mValue.New(),mValue.New(),mValue.New()};
            _xyzw[0]._set(xyz._xyzw[0]);
            _xyzw[1]._set(xyz._xyzw[1]);
            _xyzw[2]._set(xyz._xyzw[2]);
            // _xyzw[3]._set(0);
        }

        public mVector3(int x=0,int y=0,int z=0, bool isReadOnly=false)
        {
            this.IsReadOnly = isReadOnly;

            // if(_xyzw == null) _xyzw = new mValue[4]{mValue.New(),mValue.New(),mValue.New(),mValue.New()};
            _xyzw = new mValue[4]{mValue.New(),mValue.New(),mValue.New(),mValue.New()};
            _xyzw[0]._set(x);
            _xyzw[1]._set(y);
            _xyzw[2]._set(z);
            // _xyzw[3]._set(0);
        }
        public mVector3(float x,float y,float z, bool isReadOnly=false)
        {
            this.IsReadOnly = isReadOnly;

            // if(_xyzw == null) _xyzw = new mValue[4]{mValue.New(),mValue.New(),mValue.New(),mValue.New()};
            _xyzw = new mValue[4]{mValue.New(),mValue.New(),mValue.New(),mValue.New()};
            _xyzw[0]._set(x);
            _xyzw[1]._set(y);
            _xyzw[2]._set(z);
            // _xyzw[3]._set(0);
        }

        public mVector3 _copy(mVector3 vec)
        {
            CheckReadOnly();
            _xyzw[0]._copy(vec.x);
            _xyzw[1]._copy(vec.y);
            _xyzw[2]._copy(vec.z);
            return this;
        }
        public mVector3 clone()
        {
            return new mVector3(_xyzw[0],_xyzw[1],_xyzw[2]);
        }

        public mVector3 _add(mVector3 vec)
        {
            CheckReadOnly();
            _xyzw[0]._add(vec.x);
            _xyzw[1]._add(vec.y);
            _xyzw[2]._add(vec.z);
            return this;
        }

        public mVector3 _subtract(mVector3 vec)
        {
            CheckReadOnly();
            _xyzw[0]._subtract(vec.x);
            _xyzw[1]._subtract(vec.y);
            _xyzw[2]._subtract(vec.z);
            return this;
        }

        public mVector3 _subtract(mValue value)
        {
            CheckReadOnly();
            _xyzw[0]._subtract(value);
            _xyzw[1]._subtract(value);
            _xyzw[2]._subtract(value);
            return this;
        }

        public mVector3 _multiply(mVector3 vec)
        {
            CheckReadOnly();
            _xyzw[0]._multiply(vec.x);
            _xyzw[1]._multiply(vec.y);
            _xyzw[2]._multiply(vec.z);
            return this;
        }

        public mVector3 _multiply(mValue value)
        {
            CheckReadOnly();
            _xyzw[0]._multiply(value);
            _xyzw[1]._multiply(value);
            _xyzw[2]._multiply(value);
            return this;
        }

        public mVector3 _divide(mVector3 vec)
        {
            CheckReadOnly();
            _xyzw[0]._divide(vec.x);
            _xyzw[1]._divide(vec.y);
            _xyzw[2]._divide(vec.z);
            return this;
        }

        public mVector3 _divide(mValue value)
        {
            CheckReadOnly();
            _xyzw[0]._divide(value);
            _xyzw[1]._divide(value);
            _xyzw[2]._divide(value);
            return this;
        }

        public mVector3 _normalize()
        {
            CheckReadOnly();
            var magnitude = this.distance();
            this._divide(magnitude);
            return this;
        }

        public mVector3 add(mVector3 vec)
        {
            return this.clone()._add(vec);
            // return new mVector3(_xyzw[0].add(vec.x),_xyzw[1].add(vec.y),_xyzw[2].add(vec.z));
        }

        override public string ToString() {
            // return $"mVector({_xyzw[0].ToFloat()},{_xyzw[1].ToFloat()},{_xyzw[2].ToFloat()})";
            return "mVector("+_xyzw[0].ToFloat()+","+_xyzw[1].ToFloat()+","+_xyzw[2].ToFloat()+")";
        }

        internal mVector3 multiply(mVector3 vec)
        {
            return this.clone()._multiply(vec);
            // return new mVector3(_xyzw[0].multiply(vec.x),_xyzw[1].multiply(vec.y),_xyzw[2].multiply(vec.z));
        }
        internal mVector3 multiply(mValue value)
        {
            return this.clone()._multiply(value);
            // return new mVector3(_xyzw[0].multiply(vec.x),_xyzw[1].multiply(vec.y),_xyzw[2].multiply(vec.z));
        }

        internal mVector3 subtract(mVector3 vec)
        {
            return this.clone()._subtract(vec);
            // return new mVector3(_xyzw[0].subtract(vec.x),_xyzw[1].subtract(vec.y),_xyzw[2].subtract(vec.z));
        }

        internal mVector3 divide(mVector3 vec)
        {
            return this.clone()._divide(vec);
            // return new mVector3(_xyzw[0].divide(vec.x),_xyzw[1].divide(vec.y),_xyzw[2].divide(vec.z));
        }

        internal mVector3 divide(float value)
        {
            return this.clone()._divide(new mValue(value));
        }

        internal mVector3 divide(mValue value)
        {
            return this.clone()._divide(value);
            // return new mVector3(_xyzw[0].divide(vec.x),_xyzw[1].divide(vec.y),_xyzw[2].divide(vec.z));
        }

        public mValue dot(mVector3 vec)
        {
            return _xyzw[0].clone()._multiply(vec.x)._add(_xyzw[1].multiply(vec.y))._add(_xyzw[2].multiply(vec.z));
        }

        internal mVector3 cross(mVector3 rotZ)
        {
            return new mVector3(this._xyzw[1].multiply(rotZ._xyzw[2])._subtract(this._xyzw[2].multiply(rotZ._xyzw[1])),
                                this._xyzw[2].multiply(rotZ._xyzw[0])._subtract(this._xyzw[0].multiply(rotZ._xyzw[2])),
                                this._xyzw[0].multiply(rotZ._xyzw[1])._subtract(this._xyzw[1].multiply(rotZ._xyzw[0])));
        }

        public mValue magnitude()
        {
            return _xyzw[0].square()._add(_xyzw[1].square())._add(_xyzw[2].square());
        }

        public mValue distance()
        {
            // return mValue.New((float)Math.Sqrt(_xyzw[0].square()._add(_xyzw[1].square())._add(_xyzw[2].square()).ToFloat()));
            // return mValue.New(Approximate.Sqrt2(_xyzw[0].square()._add(_xyzw[1].square())._add(_xyzw[2].square()).ToFloat()));
            // return Approximate.Sqrtf(_xyzw[0].square()._add(_xyzw[1].square())._add(_xyzw[2].square()));
            return Approximate.Sqrtf(magnitude());
        }

        public mVector3 normalize()
        {
            return this.clone()._normalize();
        }

        internal bool isZero()
        {
            return _xyzw[0].Raw == 0 && _xyzw[1].Raw == 0 && _xyzw[2].Raw == 0;
        }

        internal mVector4 ToVector4()
        {
            return new mVector4(this);
        }

        internal void _set(float x, float y, float z)
        {
            CheckReadOnly();

            _xyzw[0]._set(x);
            _xyzw[1]._set(y);
            _xyzw[2]._set(z);
        }


        internal void _set(mVector3 vec)
        {
            CheckReadOnly();

            _xyzw[0]._set(vec.x);
            _xyzw[1]._set(vec.y);
            _xyzw[2]._set(vec.z);
        }

        internal void _zero()
        {
            CheckReadOnly();

            _xyzw[0]._zero();
            _xyzw[1]._zero();
            _xyzw[2]._zero();
        }

        internal mVector3 _abs()
        {
            CheckReadOnly();

            _xyzw[0]._abs();
            _xyzw[1]._abs();
            _xyzw[2]._abs();
            return this;
        }

        internal mVector3 _sign()
        {
            CheckReadOnly();
            _xyzw[0]._sign();
            _xyzw[1]._sign();
            _xyzw[2]._sign();
            return this;
        }

        internal mVector3 abs()
        {
            return (new mVector3(this))._abs();
        }

        internal mVector3 round()
        {
            return (new mVector3(this))._round();
        }

        private mVector3 _round()
        {
            CheckReadOnly();
            _xyzw[0]._round();
            _xyzw[1]._round();
            _xyzw[2]._round();
            return this;
        }

        internal mVector3 _negative()
        {
            CheckReadOnly();
            _xyzw[0]._negative();
            _xyzw[1]._negative();
            _xyzw[2]._negative();
            return this;
        }

        internal mVector3 sign()
        {
            return new mVector3(this)._sign();
        }

        internal mVector3 negative()
        {
            return new mVector3(this)._negative();
        }

        internal static mVector3 New(mVector3 vec)
        {
            return new mVector3(vec);
        }

        internal mVector2 XZasXY()
        {
            return new mVector2(x, z);
        }

        public static mVector3 operator - (mVector3 vec1,mVector3 vec2)
        {
            return vec1.subtract(vec2);
        }

        public static mVector3 operator + (mVector3 vec1,mVector3 vec2)
        {
            return vec1.add(vec2);
        }

        public static mVector3 operator * (mVector3 vec1,mVector3 vec2)
        {
            return vec1.multiply(vec2);
        }

        public static mVector3 operator / (mVector3 vec1,mVector3 vec2)
        {
            return vec1.divide(vec2);
        }


        public static mVector3 operator * (mVector3 vec,mValue value)
        {
            return vec.multiply(value);
        }
        public static mVector3 operator * (mValue value,mVector3 vec)
        {
            return vec.multiply(value);
        }
        public static mVector3 operator / (mVector3 vec,mValue value)
        {
            return vec.divide(value);
        }

        public static bool operator == (mVector3 a, mVector3 b)
        {
            return a?.x == b?.x && a?.y == b?.y && a?.z == b?.z;
        }

        public static bool operator != (mVector3 a, mVector3 b)
        {
            return a?.x != b?.x || a?.y != b?.y || a?.z != b?.z;
        }
    }
#endregion
}