using System;
using System.Collections.Generic;
using UnityEngine;

namespace CharacterCustomization
{
    [Serializable]
    public class HairOption
    {
        public string id;
        public string displayName;
        public GameObject prefab;
    }

    /// <summary>
    /// Handles skin tone and hair (style + color) — the two appearance traits that
    /// aren't expressed as blend shapes.
    /// </summary>
    public class AppearanceController : MonoBehaviour
    {
        [SerializeField] private Renderer bodyRenderer;
        [SerializeField] private string skinColorProperty = "_BaseColor";

        [SerializeField] private Transform hairAttachPoint;
        [SerializeField] private List<HairOption> hairOptions = new List<HairOption>();
        [SerializeField] private string hairColorProperty = "_BaseColor";

        private MaterialPropertyBlock propBlock;
        private GameObject currentHairInstance;
        private HairOption currentHair;

        public Color CurrentSkinColor { get; private set; } = Color.white;
        public string CurrentHairId => currentHair?.id ?? string.Empty;
        public Color CurrentHairColor { get; private set; } = Color.black;

        private void Awake()
        {
            propBlock = new MaterialPropertyBlock();
        }

        public void SetSkinColor(Color color)
        {
            CurrentSkinColor = color;

            if (bodyRenderer == null)
            {
                return;
            }

            bodyRenderer.GetPropertyBlock(propBlock);
            propBlock.SetColor(skinColorProperty, color);
            bodyRenderer.SetPropertyBlock(propBlock);
        }

        public void SetHair(string hairId, Color color)
        {
            var option = hairOptions.Find(h => h.id == hairId);

            if (option == null || option.prefab == null)
            {
                if (currentHairInstance != null)
                {
                    Destroy(currentHairInstance);
                }

                currentHairInstance = null;
                currentHair = null;
                return;
            }

            if (currentHair != option)
            {
                if (currentHairInstance != null)
                {
                    Destroy(currentHairInstance);
                }

                currentHairInstance = Instantiate(option.prefab, hairAttachPoint);
                currentHairInstance.transform.localPosition = Vector3.zero;
                currentHairInstance.transform.localRotation = Quaternion.identity;
                currentHair = option;
            }

            SetHairColor(color);
        }

        public void SetHairColor(Color color)
        {
            CurrentHairColor = color;

            if (currentHairInstance == null)
            {
                return;
            }

            var renderer = currentHairInstance.GetComponentInChildren<Renderer>();
            if (renderer == null)
            {
                return;
            }

            renderer.GetPropertyBlock(propBlock);
            propBlock.SetColor(hairColorProperty, color);
            renderer.SetPropertyBlock(propBlock);
        }
    }
}
